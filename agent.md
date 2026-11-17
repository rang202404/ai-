# agent.md — 项目级 AI 协作契约

> 本文件是本项目对**任何 AI 助手（含 DeepSeek Harness 驱动的 agent）**的最高约束。
> 进入本项目先读本文件，再读 `AI与大数据/01-事实基准.md` 与 `AI与大数据/05-幻觉防线与回答规则.md`。
> 与本文件冲突的“模型记忆”“常识推断”“网上印象”一律无效。

## 1. 项目是什么

`ai-bigdata-rag` 是一个**以 GitHub 公共仓库为语料源、零第三方运行时依赖**的检索增强生成（RAG）示例项目：

- 语料：3 个开源仓库的固定 commit（见 `AI与大数据/03-数据源与语料许可.md`）；
- 检索：BM25 + 字符 n-gram 哈希向量，RRF 融合；
- 生成：可选 DeepSeek API；无 Key 时降级为**逐字引用**，不生成新事实；
- 产物：可执行问答 CLI，以及把回答中的代码块落盘为 `*.py`。

## 2. 事实优先级（从高到低）

1. 当前文件的真实内容 & 可复现命令输出（`python -m pytest`、`python -m rag.cli stats`）；
2. `data/corpus/*.json` 中记录的 commit / license / 文件内容；
3. `AI与大数据/01-事实基准.md`；
4. 本文件与 `AI与大数据/` 其他文档；
5. 模型的先验知识（**仅在 1–4 都没有时可用，且必须标注"未在项目中验证"**）。

## 3. 硬性规则

- **禁止编造**：不得虚构 API、函数名、参数、版本号、许可证、commit、文件路径、URL。
- **无据拒答**：语料未覆盖的问题必须回答“语料中未检索到”，并说明边界，不得用常识补全。
- **必须引用**：任何来自语料的事实，必须带 `[仓库:路径:起止行]`；引用必须能在 `data/index/index.json.gz` 中回溯。
- **不许假装执行**：未运行的命令、未通过的测试、未抓取的仓库，不得写进“验证记录”。
- **不改事实基准**：`AI与大数据/01-事实基准.md` 只能由人确认后修改；AI 只能追加“变更记录”并在验证后更新。
- **不扩依赖**：运行期仅用 Python 标准库；新增第三方依赖必须先改 `environment.yml` 与 `requirements.txt`，并说明理由。
- **不改语料源**：新增/替换 GitHub 仓库必须同时更新 `rag/config.py` 的 `DEFAULT_REPOS` 与本契约文档。

## 4. 目录地图（真实存在，勿臆测）

| 路径 | 作用 |
| --- | --- |
| `agent.md` | 本契约 |
| `AI与大数据/` | 事实基准、技术栈、语料许可、RAG 规范、反幻觉规则、验收标准、术语表 |
| `rag/` | 核心实现：config / textutil / github_source / chunking / index / retrieve / llm / pipeline / cli |
| `scripts/` | 采集、建索引、问答、验收四个入口 |
| `tests/` | pytest 测试（22 个用例） |
| `docs/` | GitHub 账号、Git 安装配置、pull/push、LICENSE 说明、验证记录 |
| `data/corpus/` | 抓取缓存（git 忽略），每仓一个 json |
| `data/index/` | 索引（git 忽略） |
| `examples/generated/` | `--save-code` 生成的 .py 产物 |
| `tools/` | 便携式 Git（git 忽略），仅本机验证用 |

## 5. 常用命令（全部已在本机验证）

```powershell
# 激活环境
(& "D:\working area\shell\condabin\conda-hook.ps1"); conda activate test

# 采集 / 重建索引 / 问答 / 带引用落盘代码
python -m rag.cli fetch
python -m rag.cli index
python -m rag.cli ask "Flask 如何注册返回 JSON 的路由？" --top-k 5
python -m rag.cli ask "FastAPI 如何用 Depends 定义依赖？" --save-code examples/generated/depends_demo.py

# 测试与验收
python -m pytest tests -q
python scripts/evaluate.py
```

## 6. 工作流程（AI 必须按序执行）

1. 读本文件与 `01-事实基准.md`；
2. 用命令核实（`python --version`、`python -m rag.cli stats`、`pytest`），**不要凭印象**；
3. 修改代码前先看 `02-技术栈与运行环境.md` 的约束；
4. 改动后必须跑 `pytest`，涉及检索再跑 `scripts/evaluate.py`；
5. 在 `docs/05-验证记录.md` 追加真实输出（含时间、命令、结果），失败也要如实记录；
6. 若发现文档与事实冲突，以事实为准并更新文档。

## 7. 完成定义（DoD）

- [ ] `python -m pytest tests -q` 全绿；
- [ ] `python scripts/evaluate.py` 5/5 通过；
- [ ] `python -m rag.cli stats` 能输出 chunks/vocab/repos；
- [ ] `examples/generated/*.py` 至少有一个文件能通过 `ast.parse`；
- [ ] 所有回答含可回溯引用，越界问题被拒答；
- [ ] `docs/05-验证记录.md` 与本次运行一致。

## 8. 变更记录

| 日期 | 变更 | 验证 |
| --- | --- | --- |
| 2026-11-17 | 初始化项目契约 | 待首次运行后补 |
