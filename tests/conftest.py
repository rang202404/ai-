"""pytest 公共配置：把项目根目录加入 sys.path，并提供合成语料 fixture。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.chunking import Chunk  # noqa: E402
from rag.index import Index  # noqa: E402


@pytest.fixture
def chunks() -> list[Chunk]:
    return [
        Chunk(
            repo="demo/alpha",
            path="src/app.py",
            lang="python",
            start_line=1,
            end_line=6,
            text='@app.get("/health")\ndef health():\n    return {"status": "ok"}',
        ),
        Chunk(
            repo="demo/alpha",
            path="README.md",
            lang="markdown",
            start_line=1,
            end_line=6,
            text="# Alpha\n\nUse `timeout=5` to avoid hanging requests.\nRetry with backoff.",
        ),
        Chunk(
            repo="demo/beta",
            path="client.py",
            lang="python",
            start_line=10,
            end_line=16,
            text="def fetch(url, timeout=5):\n    return session.get(url, timeout=timeout)",
        ),
    ]


@pytest.fixture
def index(chunks: list[Chunk]) -> Index:
    return Index.build(chunks)
