"""检索层：召回、覆盖率判定、上下文拼装。

拒答是"反幻觉"的第一道闸门：
  - 查询词项在语料倒排表中几乎不存在 -> 直接拒答，不交给大模型猜；
  - 命中片段必须能定位到 仓库/文件/行号，否则不得进入上下文。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import config
from .index import Index
from .textutil import query_terms, snippet

# 覆盖率只统计"英文/数字"关键词：中文单字几乎不可能出现在英文语料中，
# 若把它们计入分母，任何中文提问都会被误判为低覆盖。中文提问请附带英文关键词。
ASCII_TERM_RE = re.compile(r"^[a-z0-9_]{2,}$")


@dataclass
class Hit:
    chunk: object
    bm25: float
    vector: float
    fused: float

    @property
    def citation(self) -> str:
        c = self.chunk
        return f"[{c.repo}:{c.path}:{c.start_line}-{c.end_line}]"


@dataclass
class RetrievalResult:
    question: str
    hits: list[Hit] = field(default_factory=list)
    coverage: float = 0.0
    matched_terms: list[str] = field(default_factory=list)
    refused: bool = False
    reason: str = ""


class Retriever:
    def __init__(self, index: Index, top_k: int = config.TOP_K, min_coverage: float = config.MIN_COVERAGE):
        self.index = index
        self.top_k = top_k
        self.min_coverage = min_coverage
        self._sources = {item["full_name"]: item for item in index.meta.get("sources", [])}

    # ------------------------------------------------------------ 元数据
    def source_url(self, hit: Hit) -> str:
        c = hit.chunk
        source = self._sources.get(c.repo, {})
        html = source.get("html_url", f"https://github.com/{c.repo}")
        sha = source.get("commit_sha", "HEAD")
        return f"{html}/blob/{sha}/{c.path}#L{c.start_line}-L{c.end_line}"

    def citation_block(self, hit: Hit) -> str:
        c = hit.chunk
        return (
            f"### {c.repo} :: {c.path} (L{c.start_line}-L{c.end_line})\n"
            f"URL: {self.source_url(hit)}\n\n"
            f"```{c.lang}\n{c.text}\n```"
        )

    # ------------------------------------------------------------ 召回
    def retrieve(self, question: str) -> RetrievalResult:
        question = question.strip()
        result = RetrievalResult(question=question)
        if not question:
            result.refused = True
            result.reason = "问题为空。"
            return result

        terms = query_terms(question)
        if not terms:
            result.refused = True
            result.reason = "问题中没有可检索的有效词项（可能是纯标点或停用词）。"
            return result

        matched = [term for term in terms if term in self.index.postings]
        result.matched_terms = matched

        # 优先用英文关键词计算覆盖率；纯中文提问才退回全词项覆盖率
        hard_terms = [term for term in terms if ASCII_TERM_RE.match(term)]
        if hard_terms:
            matched_hard = [term for term in hard_terms if term in self.index.postings]
            result.coverage = len(matched_hard) / len(hard_terms)
            coverage_basis = f"{len(matched_hard)}/{len(hard_terms)} 个英文关键词"
        else:
            result.coverage = len(matched) / len(terms)
            coverage_basis = f"{len(matched)}/{len(terms)} 个词项"

        result.hits = [Hit(**item) for item in self.index.search(question, top_k=self.top_k * 2)]

        # 同一文件最多保留 2 段，避免重叠切块霸榜，保证证据来自不同位置
        limited: list[Hit] = []
        per_path: dict[tuple[str, str], int] = {}
        for hit in result.hits:
            key = (hit.chunk.repo, hit.chunk.path)
            if per_path.get(key, 0) >= 2:
                continue
            per_path[key] = per_path.get(key, 0) + 1
            limited.append(hit)
            if len(limited) >= self.top_k:
                break
        result.hits = limited

        if not result.hits or result.coverage < self.min_coverage:
            repos = ", ".join(sorted({chunk.repo for chunk in self.index.chunks}))
            result.refused = True
            result.reason = (
                f"已采集语料（{repos}）与问题的关键词覆盖率仅 {result.coverage:.0%}"
                f"（{coverage_basis}），低于阈值 {self.min_coverage:.0%}，为避免编造直接拒答。"
                "建议改用英文关键词，或先运行 `python -m rag.cli fetch` 扩充语料。"
            )
            return result

        return result

    # ------------------------------------------------------------ 上下文
    def format_context(self, hits: list[Hit], max_chars: int = config.MAX_CONTEXT_CHARS) -> str:
        blocks: list[str] = []
        used = 0
        for i, hit in enumerate(hits, start=1):
            header = (
                f"[{i}] repo={hit.chunk.repo} path={hit.chunk.path} "
                f"lines={hit.chunk.start_line}-{hit.chunk.end_line} url={self.source_url(hit)}"
            )
            block = f"{header}\n{hit.chunk.text}"
            if used + len(block) > max_chars:
                break
            blocks.append(block)
            used += len(block)
        return "\n\n".join(blocks)

    def preview(self, result: RetrievalResult) -> str:
        lines = [f"覆盖率: {result.coverage:.0%}", f"命中: {len(result.hits)} 段"]
        for rank, hit in enumerate(result.hits, start=1):
            lines.append(
                f"  {rank}. {hit.citation} bm25={hit.bm25} vec={hit.vector} fused={hit.fused}"
                f"  | {snippet(hit.chunk.text, 90)}"
            )
        return "\n".join(lines)
