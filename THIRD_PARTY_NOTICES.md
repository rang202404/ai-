# 第三方语料与许可证声明

本项目从 GitHub 抓取以下仓库的**只读片段**作为 RAG 语料，用于检索与引用演示。
抓取内容不改变上游许可证；`examples/generated/*.py` 中由检索结果落盘的代码片段，
著作权仍归上游作者，使用/分发时须遵守对应许可证。

| 仓库 | 许可证 | 固定 commit | 上游许可证文件 |
| --- | --- | --- | --- |
| [pallets/flask](https://github.com/pallets/flask) | BSD-3-Clause | `49943b5a94413a530761350f04e896f76e8d620e` | https://github.com/pallets/flask/blob/main/LICENSE.txt |
| [psf/requests](https://github.com/psf/requests) | Apache-2.0 | `3c7baaa05ab4aa49cc819ce3a819d260de19c157` | https://github.com/psf/requests/blob/main/LICENSE |
| [tiangolo/fastapi](https://github.com/tiangolo/fastapi) | MIT | `a1b3be01aadc61c67edc09eed4f6cc1fcc3d3b8f` | https://github.com/fastapi/fastapi/blob/master/LICENSE |

## 义务摘要（非法律意见）

- **BSD-3-Clause**：保留版权声明、许可证文本与免责声明；不得用作者名义背书。
- **Apache-2.0**：保留版权与许可证；修改文件需标注；附带 NOTICE（如有）。
- **MIT**：保留版权与许可声明。

## 本项目如何满足

1. 每个语料片段都带 `仓库/路径/行号` 与固定 commit 的 GitHub URL，可回溯到原始文件；
2. `AI与大数据/03-数据源与语料许可.md` 记录采集与许可证校验逻辑（不匹配白名单直接拒收）；
3. `examples/generated/*.py` 头部注明来源与"许可证遵循上游仓库"；
4. 本文件汇总上游许可证与链接，随仓库一起分发。

## 不包含的内容

- 未抓取任何 `NOASSERTION` 或白名单外许可证的仓库；
- 未抓取私有仓库、未使用需要登录的接口；
- 未缓存上游的完整仓库，仅保存检索所需的少量文件片段（`data/corpus/` 已被 `.gitignore` 忽略）。
