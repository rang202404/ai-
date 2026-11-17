# ai-bigdata-rag

以 **GitHub 公共仓库为语料**、**零第三方运行时依赖**的 RAG（检索增强生成）项目：
采集固定 commit 的源码 → 切块建索引 → 双路召回 → 带引用回答 → 可落盘为 `.py`。

> 配套「反幻觉」契约：`agent.md` + `AI与大数据/`，任何 AI 协作者先读再动手。

## 快速开始

```powershell
# 1. 激活环境（conda test，Python 3.11.18）
(& "D:\working area\shell\condabin\conda-hook.ps1"); conda activate test

# 2. 采集语料（首次；已有 data/corpus 会复用缓存）
python -m rag.cli fetch

# 3. 建索引
python -m rag.cli index

# 4. 提问（--save-code 可省略路径）
python -m rag.cli ask "FastAPI 如何用 Depends 定义依赖注入？"
python -m rag.cli ask "requests 如何发送带 timeout 的 GET 请求？" --save-code examples/generated/requests_get.py

# 5. 测试与验收
python -m pytest tests -q
python scripts/evaluate.py
```

## 当前状态（2026-11-17 实测）

| 项 | 值 |
| --- | --- |
| conda 环境 | `test`（Python 3.11.18，numpy/pandas/pytest） |
| 语料 | 3 仓库，固定 commit（flask / requests / fastapi） |
| 索引 | 434 chunks，3736 词项，gzip JSON |
| 测试 | 22 passed |
| 验收 | 5/5（3 个有据可答 + 2 个越界拒答） |
| 生成产物 | `examples/generated/` 下 3 个 `.py`，均通过 `ast.parse` |

数值会随语料重建变化，以 `python -m rag.cli stats` 为准。

## 它能回答什么

```text
问题：FastAPI 如何用 Depends 定义依赖注入？
模式：extractive | 覆盖率：100% | 命中：6
回答：【抽取式引用 · 未调用大模型】…
引用：
  - [tiangolo/fastapi:fastapi/dependencies/utils.py:496-529]
```

- 语料内问题：返回原文片段/完整函数，并带 `仓库:路径:行号`；
- 语料外问题：直接拒答并给出覆盖率，不"编一个合理答案"；
- 配置 `DEEPSEEK_API_KEY` 后，才切换为归纳式生成回答。

## 目录

```text
agent.md                  AI 协作契约（事实优先级 / 禁止事项 / DoD）
AI与大数据/               事实基准、技术栈、语料许可、RAG 规范、反幻觉、验收、术语
rag/                      核心实现（9 个模块，仅标准库）
scripts/                  fetch_corpus / build_index / ask / evaluate
tests/                    22 个 pytest 用例
docs/                     GitHub 账号、Git 安装配置、pull/push、LICENSE、验证记录
examples/generated/       RAG 落盘的 .py 产物
data/                     语料与索引缓存（git 忽略）
```

## 反幻觉设计（摘要）

1. **语料白名单 + 固定 commit**：许可证不符整仓拒收；
2. **覆盖率拒答**：英文关键词命中 < 34% 直接拒绝；
3. **强制引用**：每条结论带行号，可回 GitHub 原文核对；
4. **生成/抽取双模式**：没有 Key 时只做逐字引用，并明确标注；
5. **代码 AST 自检**：落盘 `.py` 前解析，失败如实写入头部。

细节见 `AI与大数据/05-幻觉防线与回答规则.md`。

## 文档索引

| 文档 | 内容 |
| --- | --- |
| [01 事实基准](AI与大数据/01-事实基准.md) | 环境、网络、语料 sha、未知清单 |
| [02 技术栈](AI与大数据/02-技术栈与运行环境.md) | 环境激活、依赖边界、Windows 注意 |
| [03 数据源与许可](AI与大数据/03-数据源与语料许可.md) | 采集链路、选文件、许可证义务 |
| [04 RAG 契约](AI与大数据/04-RAG流水线与接口契约.md) | 算法、CLI、`.py` 产物契约 |
| [05 反幻觉](AI与大数据/05-幻觉防线与回答规则.md) | 回答格式、拒答、审计 |
| [06 验收](AI与大数据/06-验收标准与自查清单.md) | 验收用例与自查表 |
| [07 术语](AI与大数据/07-术语表.md) | 术语解释 |
| [docs/01](docs/01-GitHub账号申请说明.md) | GitHub 账号申请 |
| [docs/02](docs/02-Git安装与配置.md) | Git 安装与配置 |
| [docs/03](docs/03-pull与push操作指南.md) | pull/push 操作与演练 |
| [docs/04](docs/04-LICENSE编写说明.md) | LICENSE 编写说明 |
| [docs/05](docs/05-验证记录.md) | 本机真实输出 |

## 许可证

- 代码：MIT；
- 文档：CC BY 4.0；
- 第三方语料：遵循上游许可证，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 已知限制

- 只覆盖 3 个仓库的少量文件，不是 GitHub 全量检索；
- 未使用 embedding，语义泛化弱，中文提问需带英文关键词；
- 无 Key 时为抽取式引用，不做归纳；
- 本机 `raw.githubusercontent.com` 被阻断，采集依赖 jsDelivr 镜像（同一 commit）。

> 演示提交：来自 clone 仓库，用于验证 pull/push。

