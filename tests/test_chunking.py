from __future__ import annotations

from rag.chunking import Chunk, chunk_text


def test_chunk_text_keeps_line_numbers_within_bounds():
    text = "\n".join(f"line {i}" for i in range(1, 201))
    chunks = chunk_text("demo/alpha", "big.py", text, max_chars=400, min_chars=10, overlap_lines=2)
    assert len(chunks) > 1
    for chunk in chunks:
        assert 1 <= chunk.start_line <= chunk.end_line <= 200
        assert chunk.lang == "python"
        assert chunk.text


def test_chunk_text_overlaps_neighbours():
    text = "\n".join(f"line {i}" for i in range(1, 121))
    chunks = chunk_text("demo/alpha", "big.py", text, max_chars=300, min_chars=10, overlap_lines=3)
    assert chunks[1].start_line < chunks[0].end_line + 1


def test_chunk_text_drops_too_short_blocks():
    assert chunk_text("demo/alpha", "tiny.py", "x = 1", min_chars=60) == []


def test_chunk_text_markdown_language():
    chunks = chunk_text("demo/alpha", "README.md", "# Title\n\n" + "word " * 100, min_chars=10)
    assert chunks and chunks[0].lang == "markdown"


def test_chunk_id_is_stable():
    chunk = Chunk("demo/alpha", "src/app.py", "python", 3, 9, "pass")
    assert chunk.chunk_id == "demo/alpha:src/app.py:3-9"
