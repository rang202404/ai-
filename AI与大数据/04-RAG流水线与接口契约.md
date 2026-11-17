# 04 RAG 流水线与接口契约

## 1. 数据流

```text
GitHub(API 元数据) + jsDelivr(固定 commit 文件)
        │
        ▼
data/corpus/*.json          采集：许可证校验、选文件、固定 sha
        │
        ▼
rag/chunking.py             切块：1400 字符 / 8 行重叠 / 保留行号
        │
        ▼
rag/index.py                索引：BM25 倒排 + 字符 n-gram 哈希向量（gzip JSON）
        │
        ▼
rag/retrieve.py             召回：双路 RRF + 覆盖率判定 + 每文件限 2 段
        │
        ├── DEEPSEEK_API_KEY 存在 ──► rag/llm.py ──► 生成式回答（带引用）
        └── 不存在/失败 ───────────► 抽取式引用（逐字代码 + 引用）
        │
        ▼
rag/pipeline.py             回答对象 + *.py 落盘（AST 语法检查）
```

## 2. 模块契约

| 模块 | 输入 | 输出 | 不允许做的事 |
| --- | --- | --- | --- |
| `config.py` | 环境变量 | 常量 | 在别处硬编码路径/参数 |
| `textutil.py` | 文本 | token / 向量 | 引入分词第三方库 |
| `github_source.py` | owner/repo | corpus dict | 抓白名单外语料、静默失败 |
| `chunking.py` | 文件文本 | `Chunk` 列表 | 丢失行号 |
| `index.py` | chunks | `Index` + gzip JSON | 把索引写入 git 跟踪路径 |
| `retrieve.py` | question | hits + 覆盖率 | 无命中仍返回"答案" |
| `llm.py` | question + context | 文本 | 无 Key 时伪造生成结果 |
| `pipeline.py` | question + index | `Answer` / `.py` | 修改语料、伪造引用 |
| `cli.py` | argv | 退出码 + stdout | 吞异常返回 0 |

## 3. 切块规则

- 单块上限 `MAX_CHUNK_CHARS=1400` 字符，块间重叠 `CHUNK_OVERLAP_LINES=8` 行；
- 切口优先落在空行；若修剪后不足 15 行，退回原始窗口边界，防止产生碎片；
- 行号 1-based，`Chunk.chunk_id = 仓库:路径:起-止`；
- 小于 `MIN_CHUNK_CHARS=60` 的块丢弃。

## 4. 检索算法

### 4.1 BM25

对查询词项 `t`，文档 `d`：

```text
idf(t) = ln(1 + (N - df(t) + 0.5) / (df(t) + 0.5))
score(d) = Σ_t idf(t) * tf(t,d) * (k1 + 1) / (tf(t,d) + k1 * (1 - b + b * |d| / avgdl))
k1 = 1.5, b = 0.75
```

- 英文标识符会拆 `snake_case` / `camelCase`；中文取单字 + 相邻二元组；
- 路径词以 `PATH_FIELD_WEIGHT=2` 加权，提升"文件定位型"查询；
- `.py` 片段乘 `CODE_BOOST=1.25`，避免 README 的 "dependencies" 章节压过真实代码。

### 4.2 字符向量

去空白后取 3-gram，`blake2b` 哈希到 512 维，L2 归一化后算余弦。
用于抗拼写差异/形态变化；不做语义 embedding。

### 4.3 RRF 融合

```text
fused(d) = Σ_route 1 / (60 + rank_route(d))
```

两路各取前 `max(top_k*6, 30)`，融合后按 `top_k` 截断，再限制**同一文件最多 2 段**，
防止重叠切块霸榜。

### 4.4 覆盖率与拒答

- 仅统计英文/数字关键词（长度 ≥ 2）的命中比例；
- 纯中文提问没有英文词时，退回全部词项的命中比例；
- 覆盖率 < `MIN_COVERAGE=0.34` 或零命中 → `refused=True`，直接返回拒答原因；
- 拒答原因会列出当前语料仓库与建议动作，**不会**猜测答案。

> 设计取舍：中文单字在英文代码语料中几乎不可能命中，若计入分母会误伤所有中文提问，
> 因此中文提问必须夹带英文关键词（如 `Flask route`）。这是显式规则，不是随机行为。

## 5. 命令行契约

| 命令 | 作用 | 关键参数 | 退出码 |
| --- | --- | --- | --- |
| `python -m rag.cli fetch` | 采集语料 | `--repos`、`--refresh` | 0 / 2 |
| `python -m rag.cli index` | 切块建索引 | 无 | 0 / 2（无语料） |
| `python -m rag.cli search "q"` | 只看召回 | `--top-k` | 0 |
| `python -m rag.cli ask "q"` | 检索+回答 | `--top-k`、`--json`、`--no-llm`、`--save-code [PATH]` | 0 |
| `python -m rag.cli stats` | 索引统计 | 无 | 0 |

`--save-code` 省略路径时写入 `examples/generated/answer.py`。

## 6. `Answer` 结构

```json
{
  "question": "...",
  "answer": "...",
  "mode": "deepseek | extractive | refused",
  "refused": false,
  "coverage": 0.86,
  "citations": ["[repo:path:1-40]"],
  "note": "未检测到 DEEPSEEK_API_KEY…",
  "elapsed_ms": 12,
  "generated_at": "2026-11-17T22:38:39+08:00",
  "sources": [{"citation": "...", "bm25": 12.3, "vector": 0.42, "preview": "..."}]
}
```

## 7. `.py` 产物契约

- 头部注释包含：生成时间、模式、覆盖率、问题、全部引用、语法检查结果；
- 代码块只提取 `python`/`py` 围栏；合并块无法解析时，保留首个可独立解析的块；
- 生成前会从 corpus 原文按 AST 找到命中行所属的**完整函数/类**（≤100 行），避免半截代码；
- 落盘后立即 `ast.parse` 自检，结果写进头部；失败也照实标注，不假装成功。

## 8. 失败模式

| 现象 | 处理 |
| --- | --- |
| GitHub API 限流（403 + remaining=0） | 抛 `RateLimitError`，提示配置 `GITHUB_TOKEN` |
| jsDelivr 超时 | 重试 3 次（指数退避），仍失败则跳过该文件 |
| 许可证不符 | 整仓拒收，不写 corpus |
| 索引版本不匹配 | `Index.load` 抛错，要求重建 |
| 无 Key / 模型调用失败 | 降级抽取式引用，`note` 说明原因 |
| 覆盖率不足 | 拒答，不调用模型 |
