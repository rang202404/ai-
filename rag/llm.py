"""生成层：调用 DeepSeek（OpenAI 兼容 /chat/completions）。

没有 API Key 时本模块不生成内容，由 pipeline 使用"抽取式引用"降级路径，
保证任何情况下回答都能溯源到语料原文。
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from . import config


class LLMError(RuntimeError):
    """大模型调用失败（未配置、网络、鉴权、额度、返回格式）。"""


def is_configured() -> bool:
    return bool(os.environ.get("DEEPSEEK_API_KEY"))


def _post_chat(messages: list[dict], temperature: float, max_tokens: int) -> dict:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    payload = json.dumps(
        {
            "model": config.DEEPSEEK_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{config.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config.DEEPSEEK_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:500]
        raise LLMError(f"DeepSeek HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise LLMError(f"DeepSeek 网络错误: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise LLMError("DeepSeek 返回非 JSON 响应") from exc


def build_messages(question: str, context: str) -> list[dict]:
    user = (
        "<context>\n"
        f"{context}\n"
        "</context>\n\n"
        f"<question>\n{question}\n</question>\n\n"
        "请严格按系统提示作答：只用 context 中的信息，逐条标注 [仓库:路径:起止行]。"
        "如果 context 不足以回答，第一句就写“语料中未检索到”。"
    )
    return [
        {"role": "system", "content": config.SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def generate(question: str, context: str) -> tuple[str, str]:
    """返回 (回答文本, "deepseek")；未配置 Key 时抛 LLMError。"""
    if not is_configured():
        raise LLMError("未配置 DEEPSEEK_API_KEY")
    data = _post_chat(build_messages(question, context), config.LLM_TEMPERATURE, config.LLM_MAX_TOKENS)
    try:
        text = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"DeepSeek 响应结构异常: {str(data)[:300]}") from exc
    return text, "deepseek"
