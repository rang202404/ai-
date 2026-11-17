# 02 Git 安装与配置

> 本机实测：Windows 11，`test` conda 环境（Python 3.11.18）。
> Git 版本：**2.56.1.windows.1**，安装位置 `D:\test\tools\git`。

## 1. 本机实际安装方式（已执行）

系统原本没有 Git（`git --version` 报 CommandNotFound）。GitHub 官方安装包下载速度约 10KB/s，
conda 源也频繁超时，最终采用**便携版 MinGit + npmmirror 镜像**：

```powershell
# 1. 下载（国内镜像，实测 38MB / 4 秒）
curl.exe -L -o D:\test\tools\MinGit.zip `
  https://registry.npmmirror.com/-/binary/git-for-windows/v2.56.1.windows.1/MinGit-2.56.1-64-bit.zip

# 2. 解压
Expand-Archive -Path D:\test\tools\MinGit.zip -DestinationPath D:\test\tools\git -Force

# 3. 验证
& "D:\test\tools\git\cmd\git.exe" --version
# git version 2.56.1.windows.1
```

已把 `D:\test\tools\git\cmd` 追加到**用户级 PATH**，新开的终端可直接用 `git`：

```powershell
[Environment]::SetEnvironmentVariable(
  'PATH',
  [Environment]::GetEnvironmentVariable('PATH','User') + ';D:\test\tools\git\cmd',
  'User')
```

> 当前已运行的终端不会自动刷新 PATH；重开终端，或临时执行
> `$env:Path += ";D:\test\tools\git\cmd"`。

## 2. 其他安装方式（按需选择）

### 2.1 winget（系统级，需管理员）

```powershell
winget install --id Git.Git -e --source winget
git --version
```

### 2.2 官方安装包

下载 <https://git-scm.com/download/win>，安装时勾选：
- "Git from the command line and also from 3rd-party software"（写入 PATH）
- "Use the OpenSSL library"
- "Checkout as-is, commit Unix-style line endings"（配合 `.gitattributes`）

### 2.3 conda（在 `test` 环境中）

```powershell
conda install -n test git -y
```

本机实测：`repo.anaconda.com` 的 repodata 多次读超时，未走通；如网络正常可优先用此方式。

## 3. 最小配置（本仓库已做）

```powershell
cd D:\test
git init -b main
git config user.name  "ai-bigdata-rag demo"
git config user.email "demo@example.invalid"
git config core.quotepath false     # 中文文件名不转义
git config core.autocrlf true       # Windows 换行兼容
```

> 提交身份是**演示身份**，真实使用请改成自己的：

```powershell
git config --global user.name  "你的名字"
git config --global user.email "你的邮箱"
```

## 4. 推荐的用户级配置

```powershell
git config --global init.defaultBranch main
git config --global core.quotepath false
git config --global core.autocrlf true
git config --global pull.rebase false
git config --global credential.helper manager   # Windows 凭据管理器（需安装 GCM）
git config --global alias.lg "log --oneline --graph --decorate"
```

查看配置来源：

```powershell
git config --list --show-origin
```

配置层级：`system`（整机）→ `global`（当前用户）→ `local`（当前仓库，优先级最高）。

## 5. 身份与认证

### 5.1 用户身份

```powershell
git config user.name
git config user.email
```

提交记录里的作者信息来自这里，**不要用别人的姓名/邮箱**。

### 5.2 SSH

```powershell
ssh-keygen -t ed25519 -C "你的邮箱"
Get-Content $HOME\.ssh\id_ed25519.pub   # 上传到 GitHub
ssh -T git@github.com                   # 验证
```

### 5.3 PAT（HTTPS）

在 GitHub → Settings → Developer settings → Personal access tokens 创建，
权限最小化（`Contents: Read and write`），有效期尽量短。
推送时用户名填 GitHub 用户名，密码填 PAT。

## 6. 代理

本机 WinINET 里 `ProxyEnable=0`，Python/Git 默认直连。若开启代理，需单独给 Git 配置：

```powershell
git config --global http.proxy  http://127.0.0.1:10808
git config --global https.proxy http://127.0.0.1:10808
# 取消
git config --global --unset http.proxy
```

## 7. 验证安装

```powershell
git --version
git config --list --show-origin
git status
git log --oneline
```

## 8. 常见问题

| 现象 | 原因/处理 |
| --- | --- |
| `git` 不是内部或外部命令 | PATH 未刷新或未写入；重开终端或检查用户 PATH |
| `warning: LF will be replaced by CRLF` | `core.autocrlf` 与 `.gitattributes` 共同作用，属正常提示 |
| 中文文件名显示为 `\346\226\207` | `git config --global core.quotepath false` |
| `fatal: not a git repository` | 当前目录不是仓库根目录，`cd D:\test` |
| `unable to access ... 443` | 代理/网络问题；检查 `git config --get http.proxy` |
| `Permission denied (publickey)` | SSH 公钥未上传或未加载 |
| `Authentication failed` | PAT 过期/权限不足；重新生成 |

## 9. 验收清单

- [x] `git --version` 输出 2.56.1.windows.1
- [x] 用户级 PATH 包含 `D:\test\tools\git\cmd`
- [x] 仓库已 `git init -b main`
- [x] `user.name` / `user.email` 已设置（演示身份）
- [x] `core.quotepath`、`core.autocrlf` 已设置
- [ ] 真实姓名/邮箱（用户自行替换）
- [ ] SSH/PAT 已配置（取决于远端认证方式）
