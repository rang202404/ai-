from __future__ import annotations

from rag.index import Index
from rag.retrieve import Retriever


def test_index_builds_postings(index: Index):
    stats = index.stats()
    assert stats["chunks"] == 3
    assert "timeout" in index.postings


def test_search_finds_timeout_chunk(index: Index):
    hits = index.search("timeout retry")
    assert hits
    paths = {hit["chunk"].path for hit in hits[:3]}
    assert paths & {"README.md", "client.py"}


def test_retriever_reports_coverage(index: Index):
    result = Retriever(index).retrieve("timeout")
    assert not result.refused
    assert result.coverage == 1.0
    assert result.hits


def test_retriever_refuses_unknown_english_term(index: Index):
    result = Retriever(index).retrieve("kubernetes operator reconcile")
    assert result.refused
    assert "覆盖率" in result.reason


def test_retriever_refuses_pure_chinese_out_of_domain(index: Index):
    result = Retriever(index).retrieve("如何实现量子纠缠通信")
    assert result.refused


def test_index_roundtrip(tmp_path, index: Index):
    path = index.save(tmp_path / "index.json.gz")
    loaded = Index.load(path)
    assert loaded.stats()["chunks"] == index.stats()["chunks"]
    assert loaded.search("timeout")[0]["chunk"].path == index.search("timeout")[0]["chunk"].path
    assert loaded.meta["version"] == 1
