"""碳钢成分 -> 目标值（y）的回归示例：数据加载与校验。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# 黑板表头：C(wt%) / Cr / Ni / Mn / Si / P / S / Mo
FEATURES = ["C", "Cr", "Ni", "Mn", "Si", "P", "S", "Mo"]
TARGET = "y"
SAMPLE_COL = "sample_id"


def load_dataset(path: str | Path) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    """读取 CSV，返回 (特征, 目标, 原始表)。

    规则：
    - 必须包含 FEATURES 与 TARGET 列，缺列直接报错而不是静默补 0；
    - 缺失值保留为 NaN，由建模管线统一填补（便于统计缺失情况）；
    - TARGET 不允许为空，否则该行无法用于监督学习。
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"数据文件不存在：{path}")

    frame = pd.read_csv(path)
    required = set(FEATURES) | {TARGET}
    missing_cols = required - set(frame.columns)
    if missing_cols:
        raise ValueError(f"缺少必需列：{sorted(missing_cols)}；实际列：{list(frame.columns)}")

    for column in FEATURES + [TARGET]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    if frame[TARGET].isna().any():
        bad = frame.index[frame[TARGET].isna()].tolist()
        raise ValueError(f"目标列 {TARGET} 存在空值，行索引：{bad}")

    X = frame[FEATURES].copy()
    y = frame[TARGET].copy()
    return X, y, frame


def missing_report(frame: pd.DataFrame) -> dict[str, dict[str, float]]:
    """统计每列的缺失数量与比例，回答"这份数据到底缺了什么"。"""
    total = len(frame)
    report: dict[str, dict[str, float]] = {}
    for column in FEATURES:
        missing = int(frame[column].isna().sum())
        report[column] = {
            "missing": missing,
            "ratio": round(missing / total, 3) if total else 0.0,
        }
    return report
