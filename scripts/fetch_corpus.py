"""采集 GitHub 语料：python scripts/fetch_corpus.py [owner/repo ...]"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.github_source import fetch_defaults  # noqa: E402


def main(argv: list[str]) -> int:
    only = argv or None
    corpora = fetch_defaults(only=only)
    total = sum(len(item["files"]) for item in corpora)
    print(f"\n完成：{len(corpora)} 个仓库，{total} 个文件。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
