"""命令行训练入口：python -m steel_ml.train --data data/steel_demo.csv"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib

from .data import FEATURES, load_dataset, missing_report
from .model import evaluate

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = PROJECT_ROOT / "data" / "steel_demo.csv"
DEFAULT_MODEL = PROJECT_ROOT / "models" / "steel_y.joblib"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="碳钢成分 -> y 回归（演示）")
    parser.add_argument("--data", default=str(DEFAULT_DATA), help="CSV 路径")
    parser.add_argument("--model-out", default=str(DEFAULT_MODEL), help="模型输出路径")
    parser.add_argument("--alpha", type=float, default=1.0, help="岭回归正则强度")
    args = parser.parse_args(argv)

    X, y, frame = load_dataset(args.data)
    print(f"数据：{args.data}")
    print(f"样本数：{len(frame)}；特征数：{len(FEATURES)}；目标：y")

    print("\n缺失情况（本演示数据多数成分列为空）：")
    for column, stat in missing_report(frame).items():
        print(f"  {column:<3} 缺失 {stat['missing']} 行（{stat['ratio']:.0%}）")

    result = evaluate(args.alpha, X, y)
    metrics = result["metrics"]

    print("\n交叉验证指标：")
    for key in ("n_samples", "n_features", "alpha", "cv", "mae", "rmse", "r2", "train_r2"):
        print(f"  {key:<10} {metrics[key]}")

    print("\n标准化后的岭回归系数（绝对值越大影响越强）：")
    for feature, coef in sorted(result["coefficients"].items(), key=lambda item: -abs(item[1])):
        print(f"  {feature:<3} {coef:+.4f}")

    model_path = Path(args.model_out)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "pipeline": result["pipeline"],
            "features": FEATURES,
            "target": "y",
            "metrics": metrics,
            "coefficients": result["coefficients"],
            "trained_at": result["trained_at"],
            "data_path": str(Path(args.data).resolve()),
            "note": "演示数据仅 5 行，指标无统计意义，只用于验证流程。",
        },
        model_path,
    )
    print(f"\n模型已保存：{model_path}")

    if metrics["n_samples"] < 30:
        print("\n[警告] 样本量小于 30，MAE/RMSE/R2 仅供流程演示，不能作为模型效果结论。")
    print("\n指标 JSON：")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
