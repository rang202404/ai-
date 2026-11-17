# -*- coding: utf-8 -*-
# 由 ai-bigdata-rag 生成：检索增强（RAG），语料来自 GitHub 公共仓库。
# 生成时间：2026-11-17T22:39:03+08:00
# 检索模式：extractive；命中片段：6；词项覆盖率：100%
# 问题：requests 的 get 函数如何发送请求？
# 引用来源：
#   - [psf/requests:src/requests/sessions.py:744-779]  ->  psf/requests/src/requests/sessions.py
#   - [psf/requests:src/requests/api.py:59-101]  ->  psf/requests/src/requests/api.py
#   - [psf/requests:src/requests/sessions.py:281-308]  ->  psf/requests/src/requests/sessions.py
#   - [psf/requests:README.md:1-27]  ->  psf/requests/README.md
#   - [psf/requests:src/requests/__init__.py:1-59]  ->  psf/requests/src/requests/__init__.py
#   - [psf/requests:src/requests/adapters.py:740-749]  ->  psf/requests/src/requests/adapters.py
# 代码选择：合并代码块无法解析，仅保留首个可独立解析的代码块
# 语法检查：通过（ast.parse）
# 注意：生成代码需人工复核后再用于生产；许可证遵循上游仓库。
def get(
    url: _t.UriType, params: _t.ParamsType = None, **kwargs: Unpack[_t.GetKwargs]
) -> Response:
    r"""Sends a GET request.

    :param url: URL for the new :class:`Request` object.
    :param params: (optional) Dictionary, list of tuples or bytes to send
        in the query string for the :class:`Request`.
    :param \*\*kwargs: Optional arguments that ``request`` takes.
    :return: :class:`Response <Response>` object
    :rtype: requests.Response
    """

    return request("get", url, params=params, **kwargs)
