"""索引构建与打分：BM25（词项）+ 字符 n-gram 哈希向量，双路召回。

索引是可序列化的纯 JSON（gzip 压缩）：
  meta      -> 构建时间、commit、许可证、参数，用于复现与审计
  chunks    -> 原文片段（回答与引用全靠它，不做二次抓取）
  postings  -> term -> [[chunk_idx, tf], ...]，BM25 倒排表
  char_vecs -> 每个 chunk 的哈希向量（稀疏），用于模糊/形态召回
"""

from __future__ import annotations

import gzip
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .chunking import Chunk
from .textutil import cosine, hashed_vector, query_terms, tokenize

INDEX_VERSION = 1


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class Index:
    def __init__(self, chunks: list[Chunk], meta: dict | None = None):
        self.chunks = chunks
        self.meta = meta or {}
        self.postings: dict[str, list[list[int]]] = {}
        self.doc_len: list[int] = []
        self.char_vecs: list[dict[int, float]] = []
        self.avgdl = 0.0

    # ------------------------------------------------------------ 构建
    @classmethod
    def build(cls, chunks: list[Chunk], sources: list[dict] | None = None) -> "Index":
        index = cls(chunks)
        postings: dict[str, list[list[int]]] = {}
        doc_len: list[int] = []
        char_vecs: list[dict[int, float]] = []

        for chunk_idx, chunk in enumerate(chunks):
            # 路径作为独立字段重复加权，让 "flask/app.py" 这类查询更准
            tokens = tokenize(chunk.text)
            path_tokens = tokenize(chunk.path.replace("/", " ")) * config.PATH_FIELD_WEIGHT
            all_tokens = tokens + path_tokens
            doc_len.append(len(all_tokens))

            counts: dict[str, int] = {}
            for token in all_tokens:
                counts[token] = counts.get(token, 0) + 1
            for term, tf in counts.items():
                postings.setdefault(term, []).append([chunk_idx, tf])

            char_vecs.append(hashed_vector(f"{chunk.path}\n{chunk.text}"))

        index.postings = postings
        index.doc_len = doc_len
        index.char_vecs = char_vecs
        index.avgdl = (sum(doc_len) / len(doc_len)) if doc_len else 0.0
        index.meta = {
            "version": INDEX_VERSION,
            "built_at": _now(),
            "chunk_count": len(chunks),
            "vocab_size": len(postings),
            "avg_doc_len": round(index.avgdl, 2),
            "params": {
                "max_chunk_chars": config.MAX_CHUNK_CHARS,
                "overlap_lines": config.CHUNK_OVERLAP_LINES,
                "bm25_k1": config.BM25_K1,
                "bm25_b": config.BM25_B,
                "hash_dim": config.HASH_DIM,
                "char_ngram": config.CHAR_NGRAM,
            },
            "sources": sources or [],
        }
        return index

    # ------------------------------------------------------------ 打分
    def bm25_scores(self, question: str) -> dict[int, float]:
        terms = query_terms(question)
        if not terms or not self.chunks:
            return {}
        n_docs = len(self.chunks)
        avgdl = self.avgdl or 1.0
        scores: dict[int, float] = {}
        for term in terms:
            posting = self.postings.get(term)
            if not posting:
                continue
            df = len(posting)
            idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
            for chunk_idx, tf in posting:
                dl = self.doc_len[chunk_idx] or 1
                denom = tf + config.BM25_K1 * (1 - config.BM25_B + config.BM25_B * dl / avgdl)
                score = idf * tf * (config.BM25_K1 + 1) / denom
                if self.chunks[chunk_idx].lang == "python":
                    score *= config.CODE_BOOST
                scores[chunk_idx] = scores.get(chunk_idx, 0.0) + score
        return scores

    def vector_scores(self, question: str) -> dict[int, float]:
        query_vec = hashed_vector(question)
        if not query_vec:
            return {}
        return {idx: cosine(query_vec, vec) for idx, vec in enumerate(self.char_vecs) if vec}

    def search(self, question: str, top_k: int = config.TOP_K) -> list[dict]:
        bm25 = self.bm25_scores(question)
        vec = self.vector_scores(question)

        bm25_order = sorted(bm25, key=lambda i: (-bm25[i], i))[: max(top_k * 6, 30)]
        vec_order = sorted(vec, key=lambda i: (-vec[i], i))[: max(top_k * 6, 30)]

        # Reciprocal Rank Fusion：两路排名倒数求和，避免单路分数尺度不一致
        fused: dict[int, float] = {}
        for rank, idx in enumerate(bm25_order, start=1):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (config.RRF_K + rank)
        for rank, idx in enumerate(vec_order, start=1):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (config.RRF_K + rank)

        ranked = sorted(fused, key=lambda i: (-fused[i], i))[:top_k]
        return [
            {
                "chunk": self.chunks[idx],
                "bm25": round(bm25.get(idx, 0.0), 4),
                "vector": round(vec.get(idx, 0.0), 4),
                "fused": round(fused[idx], 6),
            }
            for idx in ranked
        ]

    # ------------------------------------------------------------ 持久化
    def save(self, path: Path | None = None) -> Path:
        config.ensure_dirs()
        path = path or config.INDEX_DIR / "index.json.gz"
        payload = {
            "meta": self.meta,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "postings": self.postings,
            "doc_len": self.doc_len,
            "char_vecs": [{str(k): v for k, v in vec.items()} for vec in self.char_vecs],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
        return path

    @classmethod
    def load(cls, path: Path | None = None) -> "Index":
        path = path or config.INDEX_DIR / "index.json.gz"
        if not path.exists():
            raise FileNotFoundError(
                f"索引不存在：{path}。请先运行 `python -m rag.cli fetch` 与 `python -m rag.cli index`。"
            )
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)
        if payload.get("meta", {}).get("version") != INDEX_VERSION:
            raise ValueError(
                f"索引版本 {payload.get('meta', {}).get('version')} 与代码版本 {INDEX_VERSION} 不一致，请重建索引。"
            )
        chunks = [
            Chunk(
                repo=item["repo"],
                path=item["path"],
                lang=item["lang"],
                start_line=item["start_line"],
                end_line=item["end_line"],
                text=item["text"],
            )
            for item in payload["chunks"]
        ]
        index = cls(chunks, payload.get("meta", {}))
        index.postings = {term: [list(pair) for pair in pairs] for term, pairs in payload["postings"].items()}
        index.doc_len = payload["doc_len"]
        index.char_vecs = [{int(k): float(v) for k, v in vec.items()} for vec in payload["char_vecs"]]
        index.avgdl = index.meta.get("avg_doc_len") or (
            sum(index.doc_len) / len(index.doc_len) if index.doc_len else 0.0
        )
        return index

    def stats(self) -> dict:
        return {
            "chunks": len(self.chunks),
            "vocab": len(self.postings),
            "avg_doc_len": round(self.avgdl, 2),
            "repos": sorted({chunk.repo for chunk in self.chunks}),
            "built_at": self.meta.get("built_at"),
        }
