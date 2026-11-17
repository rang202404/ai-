"""构建索引：python scripts/build_index.py"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.chunking import chunk_corpus  # noqa: E402
from rag.github_source import load_corpora  # noqa: E402
from rag.index import Index  # noqa: E402


def main() -> int:
    corpora = load_corpora()
    if not corpora:
        print("没有语料，请先运行 scripts/fetch_corpus.py", file=sys.stderr)
        return 2
    chunks = []
    for corpus in corpora:
        chunks.extend(chunk_corpus(corpus))
    index = Index.build(
        chunks,
        sources=[
            {
                "full_name": corpus["full_name"],
                "commit_sha": corpus["commit_sha"],
                "license": corpus["license"],
                "html_url": corpus["html_url"],
            }
            for corpus in corpora
        ],
    )
    path = index.save()
    print(f"索引已写入：{path}")
    print(json.dumps(index.stats(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
