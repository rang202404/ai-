"""验收脚本：跑固定问题集，检查"有据可答"与"无据拒答"两类行为。

用法：python scripts/evaluate.py
输出：控制台摘要 + data/eval_report.json；全部通过返回 0，否则返回 1。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag import config  # noqa: E402
from rag.index import Index  # noqa: E402
from rag.pipeline import answer_question  # noqa: E402

CASES: list[dict] = [
    {
        "id": "flask-json-route",
        "question": "Flask 如何注册一个返回 JSON 的 GET 路由？",
        "expect": "answer",
    },
    {
        "id": "requests-timeout",
        "question": "requests 如何设置 timeout 并处理重试？",
        "expect": "answer",
    },
    {
        "id": "fastapi-depends",
        "question": "FastAPI 的 Depends 依赖注入怎么用？",
        "expect": "answer",
    },
    {
        "id": "off-topic-rust",
        "question": "如何用 Rust 实现零拷贝网络协议？",
        "expect": "refuse",
    },
    {
        "id": "off-topic-transformers",
        "question": "HuggingFace transformers 的 pipeline 怎么用？",
        "expect": "refuse",
    },
]

CITATION_RE = re.compile(r"\[([^\]:]+):([^\]:]+):(\d+)-(\d+)\]")


def main() -> int:
    index = Index.load()
    known = {chunk.chunk_id for chunk in index.chunks}
    results = []

    for case in CASES:
        answer = answer_question(case["question"], index, use_llm=False)
        citations_valid = True
        for citation in answer.citations:
            match = CITATION_RE.fullmatch(citation)
            chunk_id = f"{match.group(1)}:{match.group(2)}:{match.group(3)}-{match.group(4)}" if match else ""
            citations_valid = citations_valid and chunk_id in known

        if case["expect"] == "refuse":
            passed = answer.refused
            detail = "已按预期拒答" if passed else "未拒答，存在越界回答风险"
        else:
            passed = (not answer.refused) and bool(answer.hits) and bool(answer.citations) and citations_valid
            detail = (
                f"命中 {len(answer.hits)} 段，引用 {len(answer.citations)} 条，引用可回溯={citations_valid}"
                if passed
                else "未满足：需要有命中、有引用且引用可回溯"
            )

        results.append(
            {
                "id": case["id"],
                "question": case["question"],
                "expect": case["expect"],
                "mode": answer.mode,
                "coverage": round(answer.coverage, 4),
                "refused": answer.refused,
                "passed": passed,
                "detail": detail,
                "answer_preview": answer.text[:300],
            }
        )
        print(f"[{'PASS' if passed else 'FAIL'}] {case['id']}: {detail}")

    report = {
        "total": len(results),
        "passed": sum(1 for item in results if item["passed"]),
        "failed": sum(1 for item in results if not item["passed"]),
        "index_built_at": index.meta.get("built_at"),
        "cases": results,
    }
    config.ensure_dirs()
    report_path = config.DATA_DIR / "eval_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n合计 {report['passed']}/{report['total']} 通过，报告：{report_path}")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
