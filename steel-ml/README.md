# steel-ml — 碳钢成分回归（演示）

把黑板上的碳钢成分表做成一个**可运行的机器学习小项目**：CSV 数据 → 缺失值处理 → 岭回归 → 指标与预测。

> 这是流程演示，不是材料学结论。黑板只给了 5 行、且多数成分列空白，模型指标没有统计意义。

## 1. 数据来自哪里

2026-11-17 的黑板照片，转录如下（空白的格子在 CSV 里就是空值）：

| sample_id | C(wt%) | Cr | Ni | Mn | Si | P | S | Mo | y |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.10 | | | | | | | | 250 |
| 2 | 0.12 | | | | | | | | 230 |
| 3 | | | | | | | | | 225 |
| 4 | | | | | | | | | 240 |
| 5 | | | | | | | | | 250 |

**不确定项（不要当成事实）：**

- `y` 的实际含义黑板未标（可能是硬度、强度或其它指标）；
- 黑板上的 `X₁₀` 是试样编号还是别的含义未确认；
- 除 C 以外的成分列没有填写数值。

代码不替这些空白编数据：缺失就保留为 NaN，由管线统一填补，并在输出里报告缺失比例。

## 2. 数据结构

`data/steel_demo.csv` 列名固定为：

```text
sample_id, C, Cr, Ni, Mn, Si, P, S, Mo, y
```

- 特征：`C, Cr, Ni, Mn, Si, P, S, Mo`（对应黑板表头）；
- 目标：`y`；
- 缺失值为空字符串；`y` 不允许为空。

换成真实数据时，只要列名一致即可，不必改代码。

## 3. 快速开始

```powershell
(& "D:\working area\shell\condabin\conda-hook.ps1"); conda activate test
cd D:\test\steel-ml

python -m steel_ml.train --data data/steel_demo.csv
python -m steel_ml.predict --c 0.11
python -m pytest tests -q
```

依赖：`pandas`、`scikit-learn`、`joblib`（见 `requirements.txt`，`test` 环境已安装）。

## 4. 输出（实测见 docs/05 或运行日志）

```text
数据：...\data\steel_demo.csv
样本数：5；特征数：8；目标：y

交叉验证指标：
  cv         LeaveOneOut
  mae        ...
  rmse       ...
  r2         ...

标准化后的岭回归系数：
  C          ...
  ...

模型已保存：...\models\steel_y.joblib
```

具体数值以本机运行为准，本文不预先编造。

## 5. 设计说明

| 选择 | 原因 |
| --- | --- |
| 岭回归（Ridge） | 5 行样本下数值稳定、系数可解释；复杂模型必然过拟合 |
| 缺失填训练集中位数 | "空白"表示未知而不是 0 wt%；整列为空时中位数不存在，才退回 0 |
| 留一交叉验证 | 样本 ≤ 20 时用 LeaveOneOut，避免切分后训练集过小 |
| 标准化 | 各成分量纲不同（wt%），系数比较前必须标准化 |
| 指标全量输出 | MAE/RMSE/R² 一并给出，避免只挑好看的指标 |

## 6. 局限（必须看）

1. 5 个样本、2 个不同的 C 值，学不到可靠的成分-性能关系；
2. 其余 7 个成分全空，模型实际上只利用了 C；
3. `y` 的含义与单位未确认，预测值不能直接用于工程判断；
4. 交叉验证指标只能证明"流程跑通"，不能证明"模型有效"。

## 7. 换成真实数据

1. 把真实表格整理成同样列名的 CSV（或改 `steel_ml/data.py` 的 `FEATURES`）；
2. `python -m steel_ml.train --data your.csv --alpha 1.0`；
3. 样本 > 20 时自动改用 5 折交叉验证；
4. 若要用随机森林，改 `steel_ml/model.py` 的 `build_pipeline`，并同步更新本文档。

## 8. 目录

```text
steel-ml/
├── data/steel_demo.csv      黑板转录的演示数据
├── steel_ml/
│   ├── data.py              读取与校验
│   ├── model.py             管线、评估、单条预测
│   ├── train.py             训练入口
│   └── predict.py           预测入口
├── tests/test_steel_ml.py   6 个用例
├── requirements.txt
└── README.md
```

`models/` 为训练产物目录（已 git 忽略）。
