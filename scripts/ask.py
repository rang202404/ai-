"""检索问答：python scripts/ask.py "问题" [--save-code out.py]"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.index import Index  # noqa: E402
from rag.pipeline import answer_question, save_code  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GitHub 语料 RAG 问答")
    parser.add_argument("question", nargs="+")
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--save-code", metavar="PATH")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    answer = answer_question(" ".join(args.question), Index.load(), top_k=args.top_k, use_llm=not args.no_llm)
    if args.json:
        print(json.dumps(answer.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"模式：{answer.mode} | 覆盖率：{answer.coverage:.0%} | 命中：{len(answer.hits)}")
        print(answer.text)
        print("\n引用：")
        for citation in answer.citations:
            print(f"  - {citation}")
    if args.save_code:
        print(f"代码已保存：{save_code(answer, Path(args.save_code))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
