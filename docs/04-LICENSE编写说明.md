# 04 LICENSE 编写说明

## 1. 为什么必须有 LICENSE

没有 LICENSE 的仓库默认**保留所有权利**：别人不能合法复制、修改、分发。
LICENSE 明确"允许什么、要求什么、不担保什么"，也是企业采用前的必查项。

## 2. 本项目的分层许可

| 内容 | 许可证 | 文件 |
| --- | --- | --- |
| 代码（`rag/`、`scripts/`、`tests/`） | MIT | `LICENSE` 正文 |
| 文档（`agent.md`、`README.md`、`AI与大数据/`、`docs/`） | CC BY 4.0 | `LICENSE` 第 2 节 |
| 第三方语料片段 | 遵循上游 | `THIRD_PARTY_NOTICES.md` |

一个仓库可以分层授权，但必须在 LICENSE 中写清边界，否则会产生歧义。

## 3. MIT 逐段说明

```text
MIT License
Copyright (c) 2026 ai-bigdata-rag contributors
```

- 版权行格式：`Copyright (c) 年份 版权人`；
- 年份写首次发布年，或"起止年"；版权人可以是个人、公司或"contributors"；
- 不要写不存在的组织名。

```text
Permission is hereby granted, free of charge, to any person obtaining a copy ...
```

授予：免费使用、复制、修改、合并、发布、分发、再许可、销售。

```text
The above copyright notice and this permission notice shall be included ...
```

义务：所有副本/实质部分必须保留版权声明与许可声明。

```text
THE SOFTWARE IS PROVIDED "AS IS" ...
```

免责：不担保、不承担损害责任。

## 4. 如何选择许可证（简表）

| 许可证 | 特点 | 适用 |
| --- | --- | --- |
| MIT | 最短、最宽松，保留声明即可 | 工具库、示例项目（本项目） |
| Apache-2.0 | 含专利授权与 NOTICE 要求 | 企业级库 |
| BSD-3-Clause | 近似 MIT，禁止背书条款 | 框架（如 Flask） |
| MPL-2.0 | 文件级 copyleft | 需要回馈修改的库 |
| GPL-3.0 | 传染性 copyleft | 强调开源延续 |

本项目选 MIT：示例性质、希望被自由复用；文档用 CC BY 4.0 便于转载。

## 5. 第三方兼容性

本项目语料来自 MIT / Apache-2.0 / BSD-3-Clause，均可与 MIT 项目共存。
若引入 GPL 代码，整个分发物可能被迫 GPL——引入前必须评估。

`examples/generated/*.py` 含上游代码片段，**不能**仅凭本项目 MIT 就当作自有代码分发；
文件头已注明来源与"许可证遵循上游仓库"，第三方声明见 `THIRD_PARTY_NOTICES.md`。

## 6. SPDX 头（可选但推荐）

在每个源文件顶部加两行：

```python
# SPDX-FileCopyrightText: 2026 ai-bigdata-rag contributors
# SPDX-License-Identifier: MIT
```

这样机器可读，CI 也能检查。

## 7. 修改许可证的注意事项

1. 只能由版权人/权利人决定；
2. 已发布的版本不能"撤回"许可，新版本可换许可证；
3. 换证后要在 README/Release 说明，并保留旧版本 LICENSE；
4. 有外部贡献者时，换证通常需要其同意。

## 8. 常见问题

| 问题 | 回答 |
| --- | --- |
| 不写 LICENSE 行不行 | 不行，默认保留所有权利，别人无法合法使用 |
| 年份写错有影响吗 | 影响版权声明准确性，按首次发布年写 |
| 可以同时用 MIT 和 CC BY 吗 | 可以，但要像本项目一样写清各自适用范围 |
| LICENSE 需要改名吗 | 一般固定叫 `LICENSE`（或 `LICENSE.md`），便于平台识别 |
| 能删掉别人的版权声明吗 | 不能，MIT/BSD/Apache 都要求保留 |

## 9. 验收清单

- [x] 根目录存在 `LICENSE`
- [x] 代码与文档的许可范围写清
- [x] 版权行含年份与权利人
- [x] 第三方许可证单独声明
- [x] README 中链接到 LICENSE 与 THIRD_PARTY_NOTICES
- [ ] 如商用，由法务复核（本文件不构成法律意见）
