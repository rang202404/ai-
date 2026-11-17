from __future__ import annotations

from rag.index import Index
from rag.pipeline import Answer, answer_question, extract_code_blocks, save_code


def test_offline_answer_is_grounded(index: Index):
    answer = answer_question("timeout retry", index, use_llm=False)
    assert not answer.refused
    assert answer.mode == "extractive"
    assert answer.hits
    assert answer.citations
    assert "未调用大模型" in answer.text


def test_refuses_out_of_domain(index: Index):
    answer = answer_question("kubernetes operator reconcile", index, use_llm=False)
    assert answer.refused
    assert answer.mode == "refused"
    assert answer.text.startswith("无法回答")


def test_extract_code_blocks():
    text = "before\n```python\nprint('hi')\n```\nafter"
    assert extract_code_blocks(text) == ["print('hi')"]


def test_save_code_writes_importable_module(tmp_path):
    answer = Answer(
        question="demo",
        text="```python\nVALUE = 1\n\n\ndef add(a, b):\n    return a + b\n```",
        mode="deepseek",
        generated_at="2026-11-17T00:00:00+08:00",
    )
    target = save_code(answer, tmp_path / "out.py")
    source = target.read_text(encoding="utf-8")
    assert "由 ai-bigdata-rag 生成" in source
    assert "def add" in source
    compile(source, str(target), "exec")


def test_save_code_handles_answer_without_code(tmp_path):
    answer = Answer(question="q", text="没有代码", mode="extractive", generated_at="2026-11-17T00:00:00+08:00")
    target = save_code(answer, tmp_path / "empty.py")
    compile(target.read_text(encoding="utf-8"), str(target), "exec")


def test_answer_to_dict_has_sources(index: Index):
    answer = answer_question("timeout", index, use_llm=False)
    data = answer.to_dict()
    assert data["mode"] in {"extractive", "deepseek"}
    assert data["sources"] and data["citations"]
