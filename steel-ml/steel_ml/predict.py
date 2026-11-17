"""命令行预测入口：python -m steel_ml.predict --c 0.11"""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib

from .data import FEATURES
from .model import predict_one

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = PROJECT_ROOT / "models" / "steel_y.joblib"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="用训练好的模型预测 y")
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="模型路径")
    parser.add_argument("--c", type=float, default=None, help="C(wt%%)")
    parser.add_argument("--cr", type=float, default=None)
    parser.add_argument("--ni", type=float, default=None)
    parser.add_argument("--mn", type=float, default=None)
    parser.add_argument("--si", type=float, default=None)
    parser.add_argument("--p", type=float, default=None)
    parser.add_argument("--s", type=float, default=None)
    parser.add_argument("--mo", type=float, default=None)
    args = parser.parse_args(argv)

    model_path = Path(args.model)
    if not model_path.exists():
        raise FileNotFoundError(f"模型不存在：{model_path}，请先运行 python -m steel_ml.train")

    bundle = joblib.load(model_path)
    composition = {
        "C": args.c,
        "Cr": args.cr,
        "Ni": args.ni,
        "Mn": args.mn,
        "Si": args.si,
        "P": args.p,
        "S": args.s,
        "Mo": args.mo,
    }
    provided = {key: value for key, value in composition.items() if value is not None}
    if not provided:
        parser.error("至少提供一个成分，例如 --c 0.11")

    prediction = predict_one(bundle["pipeline"], composition)
    print(f"输入成分：{provided}")
    print(f"预测 y：{prediction:.2f}")
    print(f"模型训练于：{bundle['trained_at']}；样本数：{bundle['metrics']['n_samples']}")
    print(bundle.get("note", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
