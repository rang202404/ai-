"""GitHub 语料采集。

本机网络事实（2026-11-17 实测，见 AI与大数据/01-事实基准.md）：
- api.github.com 可用，但未认证配额仅 60 次/小时；
- raw.githubusercontent.com 连接超时，被网络阻断；
- cdn.jsdelivr.net 可用且不限流，可按 commit sha 读取 GitHub 仓库文件。

因此采用「GitHub API 取元数据 + jsDelivr 取文件内容」的组合：
许可证、commit sha 来自 GitHub API；文件内容来自 jsDelivr 对同一 commit 的镜像。
两者都固定在 commit sha 上，引用链接仍指向 github.com/<repo>/blob/<sha>/<path>。

约束：
- 许可证必须命中白名单，否则整仓跳过；
- 选文件聚焦 src/ 核心源码与 docs_src 示例，排除 tests/、.github/ 等噪音；
- 网络错误显式抛出，绝不静默返回空语料。
"""

from __future__ import annotations

import http.client
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import config

API_ROOT = "https://api.github.com"
JSDELIVR_DATA = "https://data.jsdelivr.com/v1/packages/gh"
JSDELIVR_CDN = "https://cdn.jsdelivr.net/gh"
USER_AGENT = "ai-bigdata-rag/1.0 (local educational RAG)"


class GitHubError(RuntimeError):
    """语料采集失败（网络、鉴权、限流、仓库不存在）。"""


class RateLimitError(GitHubError):
    """GitHub API 限流。"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class _HttpClient:
    def __init__(self, timeout: int = config.REQUEST_TIMEOUT):
        self.timeout = timeout
        self.token = os.environ.get("GITHUB_TOKEN") or None

    def _headers(self) -> dict[str, str]:
        headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _open(self, url: str) -> bytes:
        last_error: Exception | None = None
        for attempt in range(1, config.REQUEST_RETRIES + 1):
            request = urllib.request.Request(url, headers=self._headers())
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return response.read()
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", "replace")[:300]
                if exc.code in (403, 429) and exc.headers.get("X-RateLimit-Remaining") == "0":
                    reset = exc.headers.get("X-RateLimit-Reset", "?")
                    raise RateLimitError(
                        f"GitHub API 限流（HTTP {exc.code}），重置时间戳 {reset}。"
                        "可设置 GITHUB_TOKEN 提高配额。"
                    ) from exc
                if 500 <= exc.code < 600 and attempt < config.REQUEST_RETRIES:
                    last_error = exc
                    time.sleep(1.5 * attempt)
                    continue
                raise GitHubError(f"HTTP {exc.code} for {url}: {body}") from exc
            except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
                last_error = exc
                if attempt < config.REQUEST_RETRIES:
                    print(f"  [retry {attempt}/{config.REQUEST_RETRIES}] {url}: {exc}")
                    time.sleep(1.5 * attempt)
                    continue
        raise GitHubError(f"网络错误（已重试 {config.REQUEST_RETRIES} 次）{url}: {last_error}") from last_error

    def get_json(self, url: str) -> dict:
        payload = self._open(url)
        try:
            return json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError as exc:  # pragma: no cover - 防御性
            raise GitHubError(f"返回非 JSON：{url}") from exc


class GitHubClient(_HttpClient):
    """GitHub 官方 API：仓库元数据、许可证、默认分支与 HEAD sha。"""

    def repo_meta(self, owner: str, repo: str) -> dict:
        return self.get_json(f"{API_ROOT}/repos/{owner}/{repo}")

    def head_sha(self, owner: str, repo: str, branch: str) -> str:
        data = self.get_json(f"{API_ROOT}/repos/{owner}/{repo}/branches/{urllib.parse.quote(branch)}")
        return data["commit"]["sha"]


class JsDelivrClient(_HttpClient):
    """jsDelivr 的 GitHub 镜像：按 commit 列文件、取文件内容。"""

    def list_files(self, owner: str, repo: str, sha: str) -> list[dict]:
        data = self.get_json(f"{JSDELIVR_DATA}/{owner}/{repo}@{sha}?structure=flat")
        entries = []
        for item in data.get("files", []):
            path = item["name"].lstrip("/")
            entries.append({"path": path, "size": int(item.get("size", 0))})
        return entries

    def file_text(self, owner: str, repo: str, sha: str, path: str) -> str:
        quoted = urllib.parse.quote(path)
        return self._open(f"{JSDELIVR_CDN}/{owner}/{repo}@{sha}/{quoted}").decode("utf-8", "replace")


# ---------------------------------------------------------------- 选文件
EXCLUDE_FRAGMENTS = (
    "/tests/",
    "/test/",
    "/.github/",
    "/.agents/",
    "/node_modules/",
    "/vendor/",
    "/certs/",
    "/docs/",
    "/scripts/",
)
CORE_KEYWORDS = ("app.py", "routing", "dependencies", "sessions", "adapters", "blueprints", "api.py", "params")


def score_path(path: str, size: int) -> int:
    low = path.lower()
    score = 0
    if low == "readme.md":
        score += 200
    elif low.endswith(".md"):
        score += 10
    if low.startswith(("src/", "fastapi/", "lib/")):
        score += 120
    if low.startswith("docs_src/"):
        score += 100
    if low.startswith("examples/"):
        score += 60
    if low.endswith(".py"):
        score += 30
    if any(keyword in low for keyword in CORE_KEYWORDS):
        score += 25
    score -= size // 20_000
    return score


def pick_files(entries: list[dict]) -> list[dict]:
    """按路径语义打分，限制 README/docs_src 数量，返回入语料文件。"""
    candidates = [
        item
        for item in entries
        if item["path"].lower().endswith(config.ALLOWED_SUFFIXES)
        and 0 < item["size"] <= config.MAX_FILE_BYTES
        and not any(fragment in f"/{item['path'].lower()}" for fragment in EXCLUDE_FRAGMENTS)
    ]
    candidates.sort(key=lambda item: (-score_path(item["path"], item["size"]), item["path"]))

    picked: list[dict] = []
    readme_count = 0
    docs_src_count = 0
    for item in candidates:
        if len(picked) >= config.MAX_FILES_PER_REPO:
            break
        low = item["path"].lower()
        if low.endswith("readme.md"):
            if readme_count >= 1:
                continue
            readme_count += 1
        if low.startswith("docs_src/"):
            if docs_src_count >= 3:
                continue
            docs_src_count += 1
        picked.append(item)
    return picked


# ---------------------------------------------------------------- 主流程
def fetch_repo(
    owner: str,
    repo: str,
    expected_license: str | None = None,
    cached: dict | None = None,
) -> dict:
    api = GitHubClient()
    cdn = JsDelivrClient()

    if cached:
        meta = {
            "description": cached.get("description", ""),
            "html_url": cached.get("html_url", f"https://github.com/{owner}/{repo}"),
            "stargazers_count": cached.get("stars", 0),
        }
        license_info = {"spdx_id": cached["license"], "name": cached.get("license_name", "")}
        branch = cached.get("default_branch", "main")
        sha = cached["commit_sha"]
    else:
        meta = api.repo_meta(owner, repo)
        license_info = meta.get("license") or {}
        branch = meta.get("default_branch", "main")
        sha = api.head_sha(owner, repo, branch)

    spdx = license_info.get("spdx_id") or "NOASSERTION"
    if spdx not in config.ALLOWED_LICENSES:
        raise GitHubError(
            f"{owner}/{repo} 的许可证为 {spdx}，不在白名单 {sorted(config.ALLOWED_LICENSES)} 内，拒绝入库。"
        )
    if expected_license and spdx != expected_license:
        raise GitHubError(
            f"{owner}/{repo} 许可证与预期不符：实际={spdx}，预期={expected_license}。"
            "请更新 config.DEFAULT_REPOS 与事实基准文档。"
        )

    entries = cdn.list_files(owner, repo, sha)
    selected = pick_files(entries)

    files: list[dict] = []
    total_chars = 0
    for item in selected:
        if total_chars >= config.MAX_TOTAL_CHARS:
            break
        try:
            text = cdn.file_text(owner, repo, sha, item["path"])
        except GitHubError as exc:
            print(f"  [warn] 跳过 {item['path']}: {exc}")
            continue
        text = text[: config.MAX_FILE_BYTES]
        files.append(
            {
                "path": item["path"],
                "size": len(text),
                "text": text,
                "url": f"https://github.com/{owner}/{repo}/blob/{sha}/{item['path']}",
            }
        )
        total_chars += len(text)
        time.sleep(0.03)

    if not files:
        raise GitHubError(f"{owner}/{repo} 未取到任何可用文件，请检查网络或仓库结构。")

    return {
        "owner": owner,
        "repo": repo,
        "full_name": f"{owner}/{repo}",
        "description": meta.get("description") or "",
        "default_branch": branch,
        "commit_sha": sha,
        "license": spdx,
        "license_name": license_info.get("name") or "",
        "stars": meta.get("stargazers_count", 0),
        "html_url": meta.get("html_url", f"https://github.com/{owner}/{repo}"),
        "fetched_at": _now_iso(),
        "content_source": "cdn.jsdelivr.net (GitHub 仓库镜像，commit 固定)",
        "meta_source": "api.github.com",
        "files": files,
    }


# ---------------------------------------------------------------- 落盘 / 读取
def corpus_path(owner: str, repo: str, directory: Path = config.CORPUS_DIR) -> Path:
    return directory / f"{owner}__{repo}.json"


def save_corpus(corpus: dict, directory: Path = config.CORPUS_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    target = corpus_path(corpus["owner"], corpus["repo"], directory)
    target.write_text(json.dumps(corpus, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def load_corpora(directory: Path = config.CORPUS_DIR) -> list[dict]:
    if not directory.exists():
        return []
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(directory.glob("*.json"))]


def fetch_defaults(only: list[str] | None = None, refresh: bool = False) -> list[dict]:
    """抓取默认仓库并落盘；已有缓存且未指定 refresh 时直接复用。"""
    config.ensure_dirs()
    wanted = set(only or [])
    results: list[dict] = []

    for spec in config.DEFAULT_REPOS:
        full = f"{spec['owner']}/{spec['repo']}"
        if wanted and full not in wanted:
            continue

        target = corpus_path(spec["owner"], spec["repo"])
        cached = json.loads(target.read_text(encoding="utf-8")) if target.exists() else None

        if cached and not refresh:
            print(f"[fetch] {full}: 复用本地缓存（commit={cached['commit_sha'][:12]}）")
            results.append(cached)
            continue

        print(f"[fetch] {full} …")
        corpus = fetch_repo(spec["owner"], spec["repo"], spec.get("expected_license"), cached=cached)
        save_corpus(corpus)
        results.append(corpus)
        print(
            f"  -> {len(corpus['files'])} 个文件, {sum(f['size'] for f in corpus['files'])} 字符, "
            f"license={corpus['license']}, commit={corpus['commit_sha'][:12]}"
        )
    return results
