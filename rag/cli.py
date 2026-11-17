"""命令行入口：python -m rag.cli <fetch|index|ask|search|stats>。

约定：
- 关键结果打印到 stdout，便于复制进验证记录；
- 失败返回非零退出码，不吞异常；
- 零第三方依赖，conda 环境或系统 Python 均可直接运行。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import config
from .chunking import chunk_corpus
from .github_source import fetch_defaults, load_corpora
from .index import Index
from .pipeline import answer_question, save_code
from .retrieve import Retriever


def cmd_fetch(args: argparse.Namespace) -> int:
    fetch_defaults(only=args.repos or None, refresh=args.refresh)
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    corpora = load_corpora()
    if not corpora:
        print("没有可用语料。请先运行：python -m rag.cli fetch", file=sys.stderr)
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


def cmd_search(args: argparse.Namespace) -> int:
    index = Index.load()
    retriever = Retriever(index, top_k=args.top_k)
    result = retriever.retrieve(args.question)
    print(retriever.preview(result))
    if result.refused:
        print(f"\n拒答：{result.reason}")
        return 0
    for rank, hit in enumerate(result.hits, start=1):
        print(f"\n[{rank}] {retriever.citation_block(hit)}")
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    index = Index.load()
    question = " ".join(args.question)
    answer = answer_question(question, index, top_k=args.top_k, use_llm=not args.no_llm)

    if args.json:
        print(json.dumps(answer.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"问题：{answer.question}")
        print(f"模式：{answer.mode} | 覆盖率：{answer.coverage:.0%} | 耗时：{answer.elapsed_ms} ms")
        if answer.note:
            print(f"备注：{answer.note}")
        print("\n回答：")
        print(answer.text)
        print("\n引用：")
        for citation in answer.citations:
            print(f"  - {citation}")

    if args.save_code is not None:
        target = save_code(answer, Path(args.save_code))
        print(f"\n代码已保存：{target}", file=sys.stderr if args.json else sys.stdout)
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    index = Index.load()
    print(json.dumps({"index": index.stats(), "meta": index.meta}, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rag", description="GitHub 语料 RAG 工具（零第三方依赖）")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="从 GitHub 采集语料（默认三个仓库）")
    fetch.add_argument("--repos", nargs="*", help="只抓指定仓库，如 pallets/flask")
    fetch.add_argument("--refresh", action="store_true", help="忽略本地缓存，强制重新采集")
    fetch.set_defaults(func=cmd_fetch)

    index = sub.add_parser("index", help="切块并构建索引")
    index.set_defaults(func=cmd_index)

    search = sub.add_parser("search", help="只检索，不生成")
    search.add_argument("question")
    search.add_argument("--top-k", type=int, default=config.TOP_K)
    search.set_defaults(func=cmd_search)

    ask = sub.add_parser("ask", help="检索 + 生成，可选输出 .py")
    ask.add_argument("question", nargs="+")
    ask.add_argument("--top-k", type=int, default=config.TOP_K)
    ask.add_argument("--no-llm", action="store_true", help="强制抽取式回答")
    ask.add_argument("--json", action="store_true", help="输出 JSON（便于流水线消费）")
    ask.add_argument(
        "--save-code",
        nargs="?",
        const=str(config.ARTIFACT_DIR / "answer.py"),
        metavar="PATH",
        help="把回答中的 Python 代码块写成 .py（省略路径则写入 examples/generated/answer.py）",
    )
    ask.set_defaults(func=cmd_ask)

    stats = sub.add_parser("stats", help="查看索引统计")
    stats.set_defaults(func=cmd_stats)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
