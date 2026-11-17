from __future__ import annotations

from rag.textutil import (
    char_ngrams,
    cosine,
    hashed_vector,
    normalize,
    query_terms,
    tokenize,
)


def test_normalize_handles_crlf_and_tabs():
    assert normalize("a\r\nb\tc\r") == "a\nb    c\n"


def test_tokenize_splits_snake_and_camel_case():
    tokens = tokenize("get_timeout parseJSONValue")
    assert "get" in tokens and "timeout" in tokens
    assert "parse" in tokens and "json" in tokens and "value" in tokens


def test_tokenize_chinese_bigrams():
    tokens = tokenize("超时重试")
    assert "超" in tokens and "超时" in tokens and "重试" in tokens


def test_query_terms_dedup_and_preserve_order():
    assert query_terms("timeout timeout Flask") == ["timeout", "flask"]


def test_char_ngrams_and_vector_cosine():
    assert char_ngrams("abcd", 2)["ab"] == 1
    vec = hashed_vector("timeout retry")
    assert abs(cosine(vec, vec) - 1.0) < 1e-9
    assert cosine(vec, hashed_vector("完全不同的内容")) < 0.99
