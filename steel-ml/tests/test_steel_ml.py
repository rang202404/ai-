from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from steel_ml.data import FEATURES, load_dataset, missing_report
from steel_ml.model import build_pipeline, evaluate, predict_one

DEMO = Path(__file__).resolve().parents[1] / "data" / "steel_demo.csv"


def test_demo_dataset_loads():
    X, y, frame = load_dataset(DEMO)
    assert len(frame) == 5
    assert list(X.columns) == FEATURES
    assert list(y) == [250, 230, 225, 240, 250]


def test_missing_report_counts_blank_columns():
    _, _, frame = load_dataset(DEMO)
    report = missing_report(frame)
    assert report["C"]["missing"] == 3
    assert report["Mo"]["missing"] == 5


def test_pipeline_metrics_are_finite():
    X, y, _ = load_dataset(DEMO)
    result = evaluate(alpha=1.0, X=X, y=y)
    metrics = result["metrics"]
    assert metrics["n_samples"] == 5
    assert metrics["n_features"] == len(FEATURES)
    assert math.isfinite(metrics["mae"])
    assert math.isfinite(metrics["rmse"])
    assert set(result["coefficients"]) == set(FEATURES)


def test_predict_one_returns_float():
    X, y, _ = load_dataset(DEMO)
    pipeline = evaluate(alpha=1.0, X=X, y=y)["pipeline"]
    value = predict_one(pipeline, {"C": 0.11})
    assert isinstance(value, float)
    assert math.isfinite(value)


def test_missing_column_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("sample_id,C,y\n1,0.1,250\n", encoding="utf-8")
    with pytest.raises(ValueError, match="缺少必需列"):
        load_dataset(bad)


def test_target_empty_raises(tmp_path):
    bad = tmp_path / "bad_target.csv"
    header = "sample_id," + ",".join(FEATURES) + ",y\n"
    bad.write_text(header + "1,0.1,,,,,,,,\n", encoding="utf-8")
    with pytest.raises(ValueError, match="目标列"):
        load_dataset(bad)
