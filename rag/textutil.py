"""文本处理：归一化、中英文混合分词、字符 n-gram 哈希向量。

不依赖第三方分词器：英文代码 + 中文问题的混合场景下，
"英文标识符切分 + 中文单字/二元组"已足够 BM25 召回，且完全可复现。
"""

from __future__ import annotations

import hashlib
import re

from . import config

CJK_RUN_RE = re.compile(r"[\u4e00-\u9fff]+")
LATIN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?")
CAMEL_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")

STOPWORDS = frozenset(
    """a an the and or but if then else for while of to in on at by with from as is are was
    were be been being it its this that these those we you they he she i not no do does did
    can could should would will shall may might must have has had how what when where which who
    why all any each few more most other some such only own same so than too very just about
    into over after before between during through under again further once here there both
    """.split()
)


def normalize(text: str) -> str:
    if text.startswith("\ufeff"):
        text = text[1:]
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")


def _latin_tokens(word: str) -> list[str]:
    parts: list[str] = [word]
    if "_" in word:
        parts.extend(p for p in word.split("_") if p)
    parts.extend(CAMEL_RE.findall(word))
    return [p.lower() for p in parts if p]


def tokenize(text: str, *, drop_stopwords: bool = True) -> list[str]:
    """英文/数字取整词与 snake/camel 子词；中文取单字与相邻二元组。"""
    text = normalize(text)
    tokens: list[str] = []

    # 注意：必须在保留大小写的情况下切 camelCase，切完再统一小写
    for word in LATIN_RE.findall(text):
        for tok in _latin_tokens(word):
            if len(tok) < 2 and not tok.isdigit():
                continue
            if drop_stopwords and tok in STOPWORDS:
                continue
            tokens.append(tok)

    for run in CJK_RUN_RE.findall(text):
        tokens.extend(run)
        tokens.extend(run[i : i + 2] for i in range(len(run) - 1))

    return tokens


def query_terms(question: str) -> list[str]:
    """查询词项：去重且保序，用于覆盖率计算。"""
    seen: dict[str, None] = {}
    for tok in tokenize(question):
        seen.setdefault(tok, None)
    return list(seen)


def _hash_bin(feature: str) -> int:
    digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=4).digest()
    return int.from_bytes(digest, "big") % config.HASH_DIM


def char_ngrams(text: str, n: int = config.CHAR_NGRAM) -> dict[str, int]:
    flat = "".join(ch for ch in normalize(text).lower() if not ch.isspace())
    if len(flat) < n:
        return {"\x00" + flat: 1} if flat else {}
    counts: dict[str, int] = {}
    for i in range(len(flat) - n + 1):
        gram = flat[i : i + n]
        counts[gram] = counts.get(gram, 0) + 1
    return counts


def hashed_vector(text: str, n: int = config.CHAR_NGRAM) -> dict[int, float]:
    vec: dict[int, float] = {}
    for gram, count in char_ngrams(text, n).items():
        bin_id = _hash_bin(gram)
        vec[bin_id] = vec.get(bin_id, 0.0) + float(count)
    norm = sum(v * v for v in vec.values()) ** 0.5
    if norm:
        for key in vec:
            vec[key] /= norm
    return vec


def cosine(a: dict[int, float], b: dict[int, float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(k, 0.0) for k, v in a.items())


def snippet(text: str, limit: int = 240) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "..."
