"""建模管线：缺失值填补 -> 标准化 -> 岭回归。

为什么用岭回归而不是深度模型：
- 演示数据只有 5 行，复杂模型必然过拟合；
- 岭回归在特征共线/样本极少时数值稳定，系数可解释；
- 换成真实数据后，可在 build_pipeline 中替换为 RandomForest 等。
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, LeaveOneOut, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .data import FEATURES


class MedianImputer(BaseEstimator, TransformerMixin):
    """按训练集各列中位数填补缺失；整列为空时补 0。

    "空白"在数据里表示未知，不是 0 wt%，所以优先用中位数；
    整列都没有观测值时中位数不存在，才退回 0。
    """

    def __init__(self, features: list[str] | None = None):
        self.features = features or FEATURES

    def _frame(self, X) -> pd.DataFrame:
        if isinstance(X, pd.DataFrame):
            return X[self.features]
        return pd.DataFrame(np.asarray(X), columns=self.features)

    def fit(self, X, y=None):
        medians = self._frame(X).median(numeric_only=True)
        self.medians_ = medians.fillna(0.0)
        return self

    def transform(self, X):
        return self._frame(X).fillna(self.medians_).to_numpy(dtype=float)


def build_pipeline(alpha: float = 1.0) -> Pipeline:
    """构建可复现的建模管线：中位数填补 -> 标准化 -> 岭回归。"""
    return Pipeline(
        steps=[
            ("imputer", MedianImputer()),
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=alpha)),
        ]
    )


def choose_cv(n_samples: int):
    """样本很少时用留一法，样本足够时用 5 折交叉验证。"""
    if n_samples <= 20:
        return LeaveOneOut()
    return KFold(n_splits=5, shuffle=True, random_state=42)


def evaluate(alpha: float, X, y) -> dict:
    """交叉验证预测并计算指标；同时在全量数据上拟合最终模型。"""
    n_samples = len(X)
    pipeline = build_pipeline(alpha=alpha)
    cv = choose_cv(n_samples)

    y_pred_cv = cross_val_predict(pipeline, X, y, cv=cv)
    metrics = {
        "n_samples": n_samples,
        "n_features": X.shape[1],
        "alpha": alpha,
        "cv": type(cv).__name__,
        "mae": round(float(mean_absolute_error(y, y_pred_cv)), 3),
        "rmse": round(float(np.sqrt(mean_squared_error(y, y_pred_cv))), 3),
        "r2": round(float(r2_score(y, y_pred_cv)), 3) if n_samples > 1 else None,
    }

    pipeline.fit(X, y)
    metrics["train_r2"] = round(float(pipeline.score(X, y)), 3)
    coefficients = {
        feature: round(float(coef), 4)
        for feature, coef in zip(FEATURES, pipeline.named_steps["ridge"].coef_)
    }
    return {
        "pipeline": pipeline,
        "metrics": metrics,
        "coefficients": coefficients,
        "trained_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }


def predict_one(pipeline: Pipeline, composition: dict[str, float | None]) -> float:
    """对单个成分组合做预测；未提供的成分按 NaN 交给管线填补。"""
    row = {feature: composition.get(feature) for feature in FEATURES}
    frame = pd.DataFrame([row], columns=FEATURES)
    return float(pipeline.predict(frame)[0])
