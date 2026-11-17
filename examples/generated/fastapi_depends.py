# -*- coding: utf-8 -*-
# 由 ai-bigdata-rag 生成：检索增强（RAG），语料来自 GitHub 公共仓库。
# 生成时间：2026-11-17T22:38:56+08:00
# 检索模式：extractive；命中片段：5；词项覆盖率：100%
# 问题：FastAPI 如何用 Depends 定义依赖注入？
# 引用来源：
#   - [tiangolo/fastapi:README.md:475-500]  ->  tiangolo/fastapi/README.md
#   - [tiangolo/fastapi:fastapi/dependencies/utils.py:496-529]  ->  tiangolo/fastapi/fastapi/dependencies/utils.py
#   - [tiangolo/fastapi:fastapi/dependencies/utils.py:140-173]  ->  tiangolo/fastapi/fastapi/dependencies/utils.py
#   - [tiangolo/fastapi:README.md:441-482]  ->  tiangolo/fastapi/README.md
#   - [tiangolo/fastapi:fastapi/telemetry/_api.py:63-96]  ->  tiangolo/fastapi/fastapi/telemetry/_api.py
# 代码选择：合并代码块无法解析，仅保留首个可独立解析的代码块
# 语法检查：通过（ast.parse）
# 注意：生成代码需人工复核后再用于生产；许可证遵循上游仓库。
def get_parameterless_sub_dependant(*, depends: params.Depends, path: str) -> Dependant:
    assert callable(depends.dependency), (
        "A parameter-less dependency must have a callable dependency"
    )
    own_oauth_scopes: list[str] = []
    if isinstance(depends, params.Security) and depends.scopes:
        own_oauth_scopes.extend(depends.scopes)
    return get_dependant(
        path=path,
        call=depends.dependency,
        scope=depends.scope,
        concurrency=depends._concurrency,
        own_oauth_scopes=own_oauth_scopes,
    )
