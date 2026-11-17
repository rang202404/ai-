# 03 pull 与 push 操作指南

> 目标：把 `D:\test` 的提交推到 GitHub，并能安全地把远端改动拉回本地。
> 本机 Git：`D:\test\tools\git\cmd\git.exe`，版本 2.56.1.windows.1。

## 1. 先理解三个概念

| 概念 | 含义 |
| --- | --- |
| 本地仓库 | `D:\test\.git`，提交先落在这里 |
| 远端（remote） | 默认叫 `origin`，指向 GitHub 或本地裸仓库 |
| 跟踪分支 | `main` 跟踪 `origin/main`，`git push`/`git pull` 才知道往哪同步 |

## 2. 首次推送（GitHub 空仓库）

```powershell
cd D:\test
git remote add origin https://github.com/<用户名>/<仓库>.git
git push -u origin main      # -u 建立跟踪，之后可直接 git push
```

如果远端建仓时勾选了 README，会提示 `rejected (fetch first)`，先合并再推：

```powershell
git pull --rebase origin main
git push -u origin main
```

## 3. 日常循环

```powershell
git status                 # 先看改了什么
git diff                   # 看具体改动
git add <文件>             # 或 git add -A
git commit -m "type: 说明" # 提交信息写清楚做了什么
git pull --rebase origin main   # 别人可能已经推了新提交
git push origin main
```

提交信息建议用 `feat:` / `fix:` / `docs:` / `chore:` / `test:` 前缀。

## 4. fetch 与 pull 的区别

```powershell
git fetch origin        # 只下载远端对象，不动工作区
git log --oneline main..origin/main   # 看远端多了什么
git pull --rebase origin main         # 下载并变基到远端最新
```

`pull` = `fetch` + `merge`（或 `rebase`）。先 `fetch` 再决定怎么合，比直接 `pull` 安全。

## 5. 分支

```powershell
git switch -c feature/rag-eval   # 新建并切换
git push -u origin feature/rag-eval
git switch main
git merge --no-ff feature/rag-eval
git branch -d feature/rag-eval
```

## 6. 冲突处理

冲突时 Git 会在文件里标记：

```text
<<<<<<< HEAD
本地版本
=======
远端版本
>>>>>>> origin/main
```

处理步骤：

```powershell
git status                  # 列出冲突文件
# 手动编辑，保留正确内容，删除标记
git add <冲突文件>
git rebase --continue       # 若在 rebase 中
# 或 git commit             # 若在 merge 中
```

放弃本次操作：

```powershell
git rebase --abort
git merge --abort
```

## 7. 安全底线

| 禁止 | 原因 |
| --- | --- |
| `git push --force` 到共享分支 | 会覆盖别人的提交 |
| 提交 `.env`、Token、私钥 | 泄露后需立即吊销 |
| 提交 `data/`、`tools/` | 体积大、可重建，已在 `.gitignore` |
| 在 `main` 上直接跑未验证的实验 | 用分支隔离 |

确需强推时用 `--force-with-lease`（远端被更新会拒绝）：

```powershell
git push --force-with-lease origin feature/xxx
```

## 8. 本机演练实录（本地裸仓库模拟 GitHub）

由于本机没有 GitHub 账号凭据，用**裸仓库**充当远端，完整跑通 push → clone → push → pull：

```text
# 1) 建裸仓库并指向 main
git init --bare D:\test\.git-remote-demo\origin.git
git --git-dir=...\origin.git symbolic-ref HEAD refs/heads/main

# 2) 关联并首次推送
git remote add origin D:\test\.git-remote-demo\origin.git
git push -u origin main
→ branch 'main' set up to track 'origin/main'
→ * [new branch] main -> main

# 3) 克隆、在克隆里提交并推送
git clone ...\origin.git ...\clone
→ Cloning into '...\clone'... done.
git commit -m "docs: demo change from clone"
→ 7051979
git push origin main
→ 87c4370..7051979  main -> main

# 4) 主仓库 fetch + pull
git fetch origin
→ 87c4370..7051979  main -> origin/main
git pull --rebase origin main
→ Updating 87c4370..7051979
→ Fast-forward
→ README.md | 3 +++

# 5) 清理演示行并再次推送
git commit -m "chore: remove demo line after pull/push verification"
→ 9356e6f
git push origin main
→ 7051979..9356e6f  main -> main
```

结论：**推送、克隆、拉取、快进合并、跟踪分支均验证通过**。

### 8.1 GitHub 真实推送（2026-11-17 已完成）

远端仓库：<https://github.com/rang202404/ai->（空仓库，main 分支）。

```powershell
# 1) 生成专用 SSH 密钥（无口令，仅本机）
ssh-keygen -t ed25519 -f $HOME\.ssh\id_ed25519 -C "rang202404@ai-"

# 2) 把公钥加到 GitHub → Settings → SSH and GPG keys
ssh -T git@github.com
# Hi rang202404! You've successfully authenticated...

# 3) 添加远端并推送
git remote add github git@github.com:rang202404/ai-.git
git fetch github
# 远端自带 Initial commit（README.md），历史不相干，需要合并
git merge github/main --allow-unrelated-histories
# README 冲突：保留本项目版本
git checkout --ours README.md
git add README.md
git commit --no-edit
git push -u github main
# 116ac5c..e5be17a  main -> main
```

验证：

```text
git ls-remote github
e5be17a66b7cea46253b84db47c20bf47eaac0ac  refs/heads/main
```

注意：本机 `https://github.com` 的 HTTPS 请求超时（API 正常），所以走 SSH；
SSH 22 与 `ssh.github.com:443` 均可握手。

## 9. 常见错误

| 报错 | 处理 |
| --- | --- |
| `src refspec main does not match any` | 本地还没有 `main` 分支：先 commit，或 `git branch -M main` |
| `remote HEAD refers to nonexistent ref` | 裸仓库 HEAD 指向 master：`git --git-dir=... symbolic-ref HEAD refs/heads/main` |
| `rejected (fetch first)` | 远端有新提交：先 `git pull --rebase` |
| `Authentication failed` | PAT 过期或用了登录密码 |
| `Permission denied (publickey)` | SSH 公钥未上传 |
| `fatal: refusing to merge unrelated histories` | 两边历史独立：`git pull --allow-unrelated-histories` |

## 10. 验收清单

- [x] 本地仓库已初始化（main）
- [x] 已配置远端并推送
- [x] 已从克隆仓库推送并被主仓库拉取
- [x] 冲突处理与回滚命令已掌握
- [x] GitHub 真实远端推送（2026-11-17 完成，SSH，commit e5be17a）
