# 01 GitHub 账号申请说明

> 本说明按 2026-11 的 GitHub 页面整理；页面文案可能调整，**以注册页当前提示为准**。
> 本项目只需要一个免费账号即可完成 clone / push / Issue / PR。

## 1. 准备材料

| 材料 | 要求 |
| --- | --- |
| 邮箱 | 可收信；建议使用独立邮箱，不要用公司受限邮箱 |
| 用户名 | 全局唯一，字母/数字/连字符，不能以连字符开头结尾，最长 39 字符 |
| 密码 | ≥ 15 字符，或 ≥ 8 字符且包含数字与小写字母（以页面校验为准） |
| 二次验证 | 推荐手机 App（TOTP），GitHub 对贡献代码的账号要求 2FA |
| 网络 | 能访问 `github.com`（本机 GitHub API 可用，raw 域名被阻断，见 `AI与大数据/01-事实基准.md`） |

## 2. 注册步骤

1. 打开 <https://github.com/signup>；
2. 输入邮箱 → 设置密码 → 设置用户名；
3. 完成人机验证（拼图/滑块）；
4. 查收邮箱验证码（6 位），填入页面；
5. 选择账号类型：个人选 **Free**（免费版已含无限私有仓库）；
6. 跳过或完成个性化引导（Copilot/兴趣问卷均可跳过）。

用户名一旦注册成功**不能随意改名**（可改但会影响仓库地址与提交记录），建议用稳定英文名。

## 3. 开启二次验证（强烈建议）

1. 右上角头像 → **Settings**；
2. 左侧 **Password and authentication**；
3. **Two-factor authentication** → 选择 **Authenticator app**；
4. 用手机 TOTP App（如 Microsoft Authenticator、1Password）扫码；
5. 保存恢复码（Recovery codes）到离线位置。

## 4. 配置资料与安全

| 项目 | 建议 |
| --- | --- |
| Profile name | 真实姓名或常用 ID |
| Public email | 可留空，避免邮箱被抓取 |
| SSH and GPG keys | 添加上传 `~/.ssh/id_ed25519.pub`（见 `docs/02`） |
| Personal access tokens | 仅在使用 HTTPS 推送时创建，最小权限、设置过期 |
| Sessions | 定期检查并撤销陌生设备 |

## 5. 创建第一个仓库

1. 右上角 **+** → **New repository**；
2. Repository name：如 `ai-bigdata-rag`；
3. 可见性：Public（便于展示）或 Private；
4. **不要**勾选 "Add a README"（本地已有仓库时避免首推冲突）；
5. Create repository 后，页面会给出 `git remote add origin …` 的命令，复制备用。

## 6. 认证方式二选一

### 6.1 HTTPS + PAT（简单）

1. Settings → Developer settings → **Personal access tokens** → **Fine-grained tokens** → Generate new token；
2. 选择仓库范围与权限：`Contents: Read and write` 即可；有效期尽量短（如 30 天）；
3. 复制 token（只显示一次），推送时作为密码：
   ```powershell
   git push -u origin main
   # Username: 你的GitHub用户名
   # Password: 粘贴 PAT（不是登录密码）
   ```
4. 建议用 Git Credential Manager 缓存，避免明文保存：
   ```powershell
   git config --global credential.helper manager
   ```

### 6.2 SSH（推荐长期使用）

```powershell
ssh-keygen -t ed25519 -C "你的邮箱"
# 一路回车，默认 ~/.ssh/id_ed25519
Get-Content $HOME\.ssh\id_ed25519.pub
# 复制输出，粘贴到 GitHub → Settings → SSH and GPG keys → New SSH key

ssh -T git@github.com
# 期望：Hi <用户名>! You've successfully authenticated...
```

远端地址相应改为 `git@github.com:<用户名>/<仓库>.git`。

## 7. 免费账号限制（与本项目相关）

| 项目 | 免费版 |
| --- | --- |
| 仓库 | 公有/私有无限制 |
| GitHub Actions | 每月 2,000 分钟（私有仓库） |
| API 未认证 | 60 次/小时（按 IP） |
| API 认证（PAT） | 5,000 次/小时 |
| Pages | 公开仓库可用 |

本项目采集默认不带 Token（60 次/小时），配置 `GITHUB_TOKEN` 后配额提升，见 `docs/02`。

## 8. 常见问题

| 问题 | 处理 |
| --- | --- |
| 收不到验证码 | 查垃圾箱；换邮箱；等待 10 分钟后重试 |
| 用户名被占用 | 换一个（加前缀/后缀），注册后改名的成本较高 |
| 推送 403 | PAT 过期或权限不足；重新生成并只勾选必要仓库 |
| `Permission denied (publickey)` | SSH 公钥未上传，或 `ssh-agent` 未加载 |
| 2FA 丢失 | 用恢复码登录；恢复码也丢失则联系 GitHub Support |

## 9. 验收清单

- [ ] 能登录 github.com，邮箱已验证
- [ ] 已开启 2FA 并保存恢复码
- [ ] 已创建目标仓库（空仓库）
- [ ] 已配置 PAT 或 SSH，并通过 `ssh -T git@github.com` / `git ls-remote` 验证
- [ ] 知道自己的 `git@github.com:<用户名>/<仓库>.git` 地址
