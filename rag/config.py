"""项目级配置：路径、默认语料源、采集/切块/检索参数。

设计原则（对应 AI与大数据/05-幻觉防线与回答规则.md）：
1. 所有可调参数集中在此文件，避免散落在脚本里导致"文档与代码不一致"。
2. 默认语料源只放可核验的开源仓库，构建时用 GitHub API 复核准入许可证。
3. 路径全部从本文件推导，脚本可在任意工作目录运行。
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------- 路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
FACTS_DIR = PROJECT_ROOT / "AI与大数据"
DOCS_DIR = PROJECT_ROOT / "docs"

DATA_DIR = Path(os.environ.get("RAG_DATA_DIR", PROJECT_ROOT / "data")).resolve()
CORPUS_DIR = DATA_DIR / "corpus"          # 每个仓库一个 corpus json
INDEX_DIR = DATA_DIR / "index"            # index.json.gz
ARTIFACT_DIR = Path(
    os.environ.get("RAG_ARTIFACT_DIR", PROJECT_ROOT / "examples" / "generated")
).resolve()                               # 生成的 *.py 产物

# ---------------------------------------------------------------- 语料源
# expected_license 是"预期值"，真实值以 GitHub API 返回为准；
# 不一致时 fetch 直接失败，避免文档与事实漂移。
DEFAULT_REPOS: tuple[dict[str, str], ...] = (
    {
        "owner": "pallets",
        "repo": "flask",
        "expected_license": "BSD-3-Clause",
        "note": "轻量 Web 框架：源码结构清晰，适合演示代码检索",
    },
    {
        "owner": "psf",
        "repo": "requests",
        "expected_license": "Apache-2.0",
        "note": "HTTP 客户端：超时/重试/Session 等典型代码问答",
    },
    {
        "owner": "tiangolo",
        "repo": "fastapi",
        "expected_license": "MIT",
        "note": "类型驱动 API 框架：路由、依赖注入示例丰富",
    },
)

# 许可证白名单（SPDX id），不在名单内整仓跳过，控制许可风险
ALLOWED_LICENSES: frozenset[str] = frozenset(
    {"MIT", "BSD-3-Clause", "BSD-2-Clause", "Apache-2.0", "ISC", "MPL-2.0"}
)

# ---------------------------------------------------------------- 采集参数
# 注意：本机 raw.githubusercontent.com 被网络阻断（见 AI与大数据/01-事实基准.md），
# 因此统一走 api.github.com 的 contents 接口取文件内容。
REQUEST_TIMEOUT = 90          # 秒
REQUEST_RETRIES = 3           # 网络抖动重试次数
MAX_FILE_BYTES = 90_000       # 单文件上限，超过不抓（fastapi/routing.py 260KB 会被排除）
MAX_FILES_PER_REPO = 10       # 每仓库入库文件数上限
MAX_TOTAL_CHARS = 200_000     # 每仓库文本总量上限
ALLOWED_SUFFIXES = (".py", ".md")

# 路径优先级：README 与 src 优先，测试/示例次之
PATH_WEIGHTS: tuple[tuple[str, int], ...] = (
    ("readme", 100),
    ("src/", 60),
    ("lib/", 45),
    ("examples/", 30),
    ("docs/", 20),
    ("tests/", 10),
    ("test", 5),
)

# ---------------------------------------------------------------- 切块参数
MAX_CHUNK_CHARS = 1_400
MIN_CHUNK_CHARS = 60
CHUNK_OVERLAP_LINES = 8

# ---------------------------------------------------------------- 检索参数
TOP_K = 6
BM25_K1 = 1.5
BM25_B = 0.75
PATH_FIELD_WEIGHT = 2
RRF_K = 60
CHAR_NGRAM = 3
HASH_DIM = 512
MIN_COVERAGE = 0.34

# 代码优先：同一查询下 .py 片段略加权，避免 README 的 "dependencies" 章节压过真实代码
CODE_BOOST = 1.25

# ---------------------------------------------------------------- 生成参数
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_TIMEOUT = 90
MAX_CONTEXT_CHARS = 9_000
LLM_MAX_TOKENS = 1_200
LLM_TEMPERATURE = 0.0

SYSTEM_PROMPT = """你是一个严格基于检索语料回答问题的助手，服务对象是开发者。

必须遵守：
1. 只能使用 <context> 中的内容作答；context 没有的信息就直说"语料中未检索到"。
2. 每个结论后标注来源，格式：[仓库/路径:起始行-结束行]。
3. 不得编造函数名、参数、版本号、URL、许可证；不确定就写"不确定"。
4. 代码必须来自 context，可做最小拼接；不要臆造未出现的 API。
5. 如果问题超出语料范围，先说明边界，再给出语料内的最接近事实。
"""


def ensure_dirs() -> None:
    for path in (CORPUS_DIR, INDEX_DIR, ARTIFACT_DIR):
        path.mkdir(parents=True, exist_ok=True)


def repo_slug(owner: str, repo: str) -> str:
    return f"{owner}__{repo}"
