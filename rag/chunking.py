"""代码感知切块：把 GitHub 文件切成可检索、可引用的片段。

要点：
- 保留行号，引用才能落到"文件:起止行"；
- 优先在空行处断开，尽量不把函数劈成两半；
- 块间保留少量重叠行，避免跨块上下文断裂。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from . import config
from .textutil import normalize

LANG_BY_SUFFIX = {".py": "python", ".md": "markdown", ".txt": "text"}


@dataclass(frozen=True)
class Chunk:
    repo: str
    path: str
    lang: str
    start_line: int
    end_line: int
    text: str

    @property
    def chunk_id(self) -> str:
        return f"{self.repo}:{self.path}:{self.start_line}-{self.end_line}"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["id"] = self.chunk_id
        return data


def _lang(path: str) -> str:
    for suffix, lang in LANG_BY_SUFFIX.items():
        if path.lower().endswith(suffix):
            return lang
    return "text"


def _trim_to_blank_line(lines: list[str], start: int, end: int) -> int:
    """切点向前移到最近空行，最多回退 15 行，避免切断函数。"""
    j = end
    while j > start + 3 and lines[j - 1].strip():
        j -= 1
    return j if lines[j - 1].strip() == "" and j > start + 3 else end


def chunk_text(
    repo: str,
    path: str,
    text: str,
    *,
    max_chars: int = config.MAX_CHUNK_CHARS,
    min_chars: int = config.MIN_CHUNK_CHARS,
    overlap_lines: int = config.CHUNK_OVERLAP_LINES,
) -> list[Chunk]:
    text = normalize(text)
    lines = text.split("\n")
    if not any(line.strip() for line in lines):
        return []

    lang = _lang(path)
    chunks: list[Chunk] = []
    index = 0
    total = len(lines)

    while index < total:
        start = index
        chars = 0
        while index < total and chars < max_chars:
            chars += len(lines[index]) + 1
            index += 1
        end = _trim_to_blank_line(lines, start, index)
        # 修剪后块太小（< 15 行）说明切口附近没有合适空行，改用原始窗口边界，
        # 否则会反复在同一个空行处切开，产生大量 1~8 行的重复碎片。
        if end - start < 15:
            end = index
        block = "\n".join(lines[start:end]).strip("\n")
        if len(block) >= min_chars:
            chunks.append(
                Chunk(
                    repo=repo,
                    path=path,
                    lang=lang,
                    start_line=start + 1,
                    end_line=end,
                    text=block,
                )
            )
        if end >= total:
            break
        index = max(end - overlap_lines, start + 1)

    return chunks


def chunk_corpus(corpus: dict) -> list[Chunk]:
    repo = corpus["full_name"]
    chunks: list[Chunk] = []
    for file in corpus["files"]:
        chunks.extend(chunk_text(repo, file["path"], file["text"]))
    return chunks
