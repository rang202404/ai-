"""端到端 RAG：检索 ->（可选）生成 -> 带引用的回答 -> 落盘 *.py。

对外只暴露 answer_question() 与 save_code()；CLI、脚本、测试共用同一条链路，
避免"演示脚本"和"真实入口"行为不一致。
"""

from __future__ import annotations

import ast
import re
import textwrap
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import config, llm
from .index import Index
from .retrieve import Hit, RetrievalResult, Retriever
from .textutil import query_terms

CODE_BLOCK_RE = re.compile(r"```(?:python|py)\s*\n(.*?)```", re.DOTALL)
PLAIN_BLOCK_RE = re.compile(r"```\s*\n(.*?)```", re.DOTALL)


@dataclass
class Answer:
    question: str
    text: str
    mode: str                      # deepseek | extractive | refused
    hits: list[Hit] = field(default_factory=list)
    coverage: float = 0.0
    refused: bool = False
    note: str = ""
    elapsed_ms: int = 0
    generated_at: str = ""

    @property
    def citations(self) -> list[str]:
        return [hit.citation for hit in self.hits]

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.text,
            "mode": self.mode,
            "refused": self.refused,
            "coverage": round(self.coverage, 4),
            "citations": self.citations,
            "note": self.note,
            "elapsed_ms": self.elapsed_ms,
            "generated_at": self.generated_at,
            "sources": [
                {
                    "citation": hit.citation,
                    "bm25": hit.bm25,
                    "vector": hit.vector,
                    "preview": hit.chunk.text[:160].replace("\n", " "),
                }
                for hit in self.hits
            ],
        }


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# ---------------------------------------------------------------- 抽取式降级
def _best_excerpt(text: str, terms: set[str], max_lines: int = 30) -> str:
    """定位命中词所在函数/类，窗口截取完整代码段，避免只摘到零碎单词。"""
    lines = text.split("\n")
    hits = [i for i, line in enumerate(lines) if any(t in line.lower() for t in terms)]
    if not hits:
        return "\n".join(lines[:max_lines])

    center = hits[0]
    start = max(0, center - 6)
    for i in range(center, -1, -1):
        if re.match(r"^\s*(async\s+def|def|class)\s", lines[i]):
            start = i
            # 把紧邻的装饰器一并包含
            if i > 0 and lines[i - 1].lstrip().startswith("@"):
                start = i - 1
            break
        if center - i > 12:
            break

    end = min(len(lines), start + max_lines)
    for i in range(start + 1, end):
        if re.match(r"^\s*(async\s+def|def|class)\s", lines[i]) and i > start + 2:
            end = i
            break
    return "\n".join(lines[start:end])


def _corpus_texts() -> dict[tuple[str, str], str]:
    """加载 corpus 原文，用于把命中行扩展成完整函数/类。"""
    from .github_source import load_corpora

    if not hasattr(_corpus_texts, "_cache"):
        mapping: dict[tuple[str, str], str] = {}
        for corpus in load_corpora():
            for file in corpus["files"]:
                mapping[(corpus["full_name"], file["path"])] = file["text"]
        _corpus_texts._cache = mapping  # type: ignore[attr-defined]
    return _corpus_texts._cache  # type: ignore[attr-defined]


def _complete_symbol(repo: str, path: str, start: int, end: int) -> str | None:
    """用 AST 找到包含 [start, end] 的最小函数/类，返回带装饰器的完整源码。"""
    text = _corpus_texts().get((repo, path))
    if not text:
        return None
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None

    functions: list[ast.AST] = []
    classes: list[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node)
        elif isinstance(node, ast.ClassDef):
            classes.append(node)

    def _span(node: ast.AST) -> int:
        return (getattr(node, "end_lineno", None) or node.lineno) - node.lineno

    # 优先返回覆盖命中的最小函数；没有函数时才退回类
    for pool in (functions, classes):
        hits = []
        for node in pool:
            node_end = getattr(node, "end_lineno", None) or node.lineno
            overlap = min(end, node_end) - max(start, node.lineno) + 1
            if overlap > 0:
                hits.append(node)
        if hits:
            best = min(hits, key=_span)
            break
    if best is None:
        return None

    first = min([best.lineno] + [dec.lineno for dec in getattr(best, "decorator_list", [])])
    last = getattr(best, "end_lineno", best.lineno) or best.lineno
    lines = text.splitlines()
    if last - first > 100:      # 超大函数退化为片段，避免生成文件过长
        return None
    return "\n".join(lines[first - 1 : last])


def extractive_answer(question: str, hits: list[Hit]) -> str:
    """不调用大模型：直接引用最相关片段/完整函数，并逐条标注来源。"""
    terms = {term for term in query_terms(question) if len(term) >= 2}
    # 代码优先：最多 2 段源码 + 1 段文档，避免回答全是 README 描述
    code_hits = [hit for hit in hits if hit.chunk.lang == "python"][:2]
    doc_hits = [hit for hit in hits if hit.chunk.lang != "python"][:1]
    picked = (code_hits + doc_hits)[:3] or hits[:1]
    if not picked:
        return "语料中未检索到可引用的片段。"

    lines = ["【抽取式引用 · 未调用大模型】以下为检索命中的语料原文，可直接核对：", ""]
    for i, hit in enumerate(picked, start=1):
        chunk = hit.chunk
        code = _complete_symbol(chunk.repo, chunk.path, chunk.start_line, chunk.end_line)
        excerpt = code if code else _best_excerpt(chunk.text, terms)
        lines.append(f"#### {i}. {hit.citation}")
        lines.append(f"```{chunk.lang}")
        lines.append(excerpt)
        lines.append("```")
        lines.append("")
    lines.append("说明：以上内容逐字来自 GitHub 语料，未做生成式改写；配置 DEEPSEEK_API_KEY 后可获得归纳式回答。")
    return "\n".join(lines)


def answer_question(
    question: str,
    index: Index,
    *,
    top_k: int = config.TOP_K,
    use_llm: bool = True,
    retriever: Retriever | None = None,
) -> Answer:
    started = time.perf_counter()
    retriever = retriever or Retriever(index, top_k=top_k)
    retrieval: RetrievalResult = retriever.retrieve(question)

    if retrieval.refused:
        return Answer(
            question=question,
            text=f"无法回答：{retrieval.reason}",
            mode="refused",
            coverage=retrieval.coverage,
            refused=True,
            note=retrieval.reason,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            generated_at=_now(),
        )

    context = retriever.format_context(retrieval.hits)
    note = ""
    mode = "extractive"
    if use_llm and llm.is_configured():
        try:
            text, mode = llm.generate(question, context)
        except llm.LLMError as exc:
            text = extractive_answer(question, retrieval.hits)
            note = f"大模型调用失败，已降级为抽取式引用：{exc}"
    else:
        text = extractive_answer(question, retrieval.hits)
        if use_llm:
            note = "未检测到 DEEPSEEK_API_KEY，使用抽取式引用（不调用大模型）。"

    return Answer(
        question=question,
        text=text,
        mode=mode,
        hits=retrieval.hits,
        coverage=retrieval.coverage,
        note=note,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
        generated_at=_now(),
    )


# ---------------------------------------------------------------- 代码落盘
def extract_code_blocks(text: str) -> list[str]:
    """只提取带 python/py 标记的代码块；无标记时才退回普通围栏。"""
    blocks = [textwrap.dedent(block).strip("\n") for block in CODE_BLOCK_RE.findall(text) if block.strip()]
    if blocks:
        return blocks
    return [textwrap.dedent(block).strip("\n") for block in PLAIN_BLOCK_RE.findall(text) if block.strip()]


def _syntax_status(code: str) -> str:
    try:
        ast.parse(code)
        return "通过（ast.parse）"
    except SyntaxError as exc:
        return f"未通过（SyntaxError: {exc.msg}, line {exc.lineno}）"


def _parses(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def save_code(answer: Answer, target: Path, *, question: str | None = None) -> Path:
    """把回答中的代码块写成 .py；优先保留能独立解析的代码块。"""
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    question = question or answer.question
    blocks = extract_code_blocks(answer.text) if answer.mode != "refused" else []

    selection_note = ""
    if blocks:
        code = "\n\n\n".join(blocks)
        if not _parses(code):
            standalone = next((block for block in blocks if _parses(block)), None)
            if standalone is not None:
                code = standalone
                selection_note = "合并代码块无法解析，仅保留首个可独立解析的代码块"
    else:
        code = (
            '"""本次回答没有可提取的 Python 代码块。"""\n\n'
            f"# 问题：{question}\n"
            "# 请查看 CLI 输出或 JSON 结果中的回答文本。\n"
        )

    header = [
        "# -*- coding: utf-8 -*-",
        "# 由 ai-bigdata-rag 生成：检索增强（RAG），语料来自 GitHub 公共仓库。",
        f"# 生成时间：{answer.generated_at}",
        f"# 检索模式：{answer.mode}；命中片段：{len(answer.hits)}；词项覆盖率：{answer.coverage:.0%}",
        f"# 问题：{question}",
        "# 引用来源：",
    ]
    header.extend(f"#   - {hit.citation}  ->  {hit.chunk.repo}/{hit.chunk.path}" for hit in answer.hits)
    if selection_note:
        header.append(f"# 代码选择：{selection_note}")
    header.append(f"# 语法检查：{_syntax_status(code)}")
    header.append("# 注意：生成代码需人工复核后再用于生产；许可证遵循上游仓库。")
    header.append("")

    target.write_text("\n".join(header) + code + "\n", encoding="utf-8")
    return target
