# 服务器接入与运维手册

> 面向「我要连上去看一眼 / 查一次 / 改一下」的场景。部署流程在 [`deploy/README.md`](README.md)，
> 这里只讲**怎么连、连上之后能用什么、有哪些坑**。
> 核对时间：2026-11-14。

## 1. 一句话版本

```powershell
ssh -i $env:USERPROFILE\.ssh\id_ed25519_ai_coach ubuntu@123.207.50.98
```

代码在 `/opt/ai-coach`，账号是 `ubuntu`（**不是 root**，root 登录已禁）。

## 2. 两把密钥，权限不一样

| 密钥 | 位置 | 能做什么 |
|---|---|---|
| `id_ed25519_ai_coach` | `~/.ssh/` | **完整 shell**。日常排查、查库、改配置都用它 |
| `id_ed25519_ai_coach_deploy` | `~/.ssh/` | **只能执行 4 个动作**：`web` / `backend` / `verify` / `status`。带 `command=` 强制命令、`no-pty`、`no-port-forwarding`、`no-agent-forwarding`，拿不到交互 shell |

服务端 `~/.ssh/authorized_keys` 现有 4 条：1 条腾讯云预置的 rsa、2 条同名 `ai-coach-server`（历史遗留重复，可清理）、1 条受限的 `github-actions-deploy`。

> 判断要不要用部署密钥：**只是发布**用 deploy 密钥；**任何需要看/查/改**的操作必须用完整密钥。

## 3. Windows 上的连接坑（都踩过）

**必须用系统 OpenSSH，不能用 git-bash 自带的。**

```powershell
$ssh = "C:\Windows\System32\OpenSSH\ssh.exe"
$scp = "C:\Windows\System32\OpenSSH\scp.exe"
```

git-bash 的 ssh 认不出中文用户名路径（`C:\Users\万里鹏`），会报 key 找不到。

**别在 ssh 后面塞复杂命令。** PowerShell 的引号转义会吃掉 `"`、`(`、`|`，远端 bash 会报语法错。
正确做法：把脚本写成 `.sh` → `scp` 上去 → 远端执行。

```powershell
& $scp -i $key "本地\script.sh" ubuntu@123.207.50.98:/tmp/script.sh
& $ssh -i $key ubuntu@123.207.50.98 'sed -i "s/\r$//" /tmp/script.sh; bash /tmp/script.sh'
```

**传上去的脚本必须先去掉 CRLF。** Windows 写的 `.sh` 带 `\r`，bash 会报 `$'\r': command not found`。

- ✅ `sed -i "s/\r$//" file`
- ❌ `tr -d "\r"` —— 它删的是「反斜杠」和「r」两个字符，会把脚本里所有字母 `r` 删掉（踩过两次）

**本机生成的脚本编码也有讲究**：PowerShell 5.1 存含中文的 `.ps1` 要带 UTF-8 BOM；`.vbs` 必须纯 ASCII。`.sh` 交给远端跑则保持 UTF-8 无 BOM。

## 4. 连上之后常用什么

### 看状态

```bash
sudo docker compose -f /opt/ai-coach/docker-compose.yml ps
cat /opt/ai-coach/REVISION                      # 线上部署的提交
curl -s http://127.0.0.1/api/v1/health          # {"status":"ok","env":"prod"}
```

### 看日志

```bash
cd /opt/ai-coach
sudo docker compose logs -f --tail=100 backend
sudo docker compose logs --since 30m backend | grep -iE "error|warning|multi-question"
```

出题质量的几个关键词：`multi-question output detected`（检测到两问）、
`multi-question regeneration still invalid`（重生成仍不合格，保留原题）、
`regenerated question still repeated`（重复题兜底到静态题库）。

### 查数据库

库名和账号**从 `.env` 读**，不要硬编码：

```bash
cd /opt/ai-coach
U=$(grep -E '^POSTGRES_USER=' .env | cut -d= -f2)
D=$(grep -E '^POSTGRES_DATABASE=' .env | cut -d= -f2)
sudo docker compose exec -T db psql -U "$U" -d "$D" -c '\dt'
```

查最近一场面试的题目（常用）：

```bash
sudo docker compose exec -T db psql -U "$U" -d "$D" -A -F '|' -t -c \
 "SELECT round_no, left(content, 60) FROM interview_messages
  WHERE interview_id = (SELECT id FROM interview_sessions ORDER BY create_time DESC LIMIT 1)
    AND role='AI_INTERVIEWER' ORDER BY round_no;"
```

### 看/改线上配置

`/opt/ai-coach/.env`，改完要重建容器才生效：

```bash
cd /opt/ai-coach
cp .env ".env.bak.$(date +%F-%H%M)"
sed -i 's|^LLM_QUESTION_THINKING=.*|LLM_QUESTION_THINKING=disabled|' .env
sudo docker compose up -d backend
sudo docker compose exec -T backend printenv LLM_QUESTION_THINKING   # 确认容器内生效
```

当前键名：`POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DATABASE` /
`LLM_PROVIDER` / `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` / `LLM_TEMPERATURE` /
`LLM_TIMEOUT_SECONDS` / `LLM_QUESTION_THINKING`。

## 5. `/opt/ai-coach` 布局

```
backend/                后端源码（部署时整体覆盖，旧版留 backend.prev）
frontend/dist/          前端产物（nginx 只读 bind mount）
deploy/ci/              受限部署入口与四个动作脚本
docker-compose.yml      实际生效的 compose（= prebuilt-web 版，服务器不构建前端）
docker-compose.prebuilt-web.yml
.env                    配置（不入库）
REVISION                线上部署的提交号，status 以它为准
```

**两条硬约束：**

1. `frontend/dist` 是 bind mount，更新只能 `find . -mindepth 1 -delete` 清内容，**不能 `rm -rf dist && mkdir dist`**——容器挂的是启动那一刻的 inode，重建目录会让 nginx 指向不存在的路径，整站 404。
2. 服务器**访问不了 GitHub**（`git ls-remote` 直接超时）。所以不要指望在服务器 `git pull`，源码一律从本机/CI 用 tar 通过 stdin 传过去。

## 6. REVISION 的约定

`REVISION` 记的是「当前线上跑的提交号」，`deploy/ci/status.sh` 以它为准。

- `backend` 动作会自动写
- **只发前端不会写**——发完前端记得手动同步，否则 REVISION 会落后，让人误判线上版本

```bash
ssh ... "printf '%s' <sha> > /opt/ai-coach/REVISION"
```

## 7. 本机这边我用的辅助脚本

都在 `E:\hanakoWorkspace\ai-coach-deploy\`，不是仓库的一部分：

| 脚本 | 用途 |
|---|---|
| `deploy-web-now.sh` | 服务器侧：备份 → 清 dist 内容 → 解包 `/tmp/dist-new.tgz` → 自检 |
| `thinking-off.sh` / `revert-thinking.sh` | 切 `LLM_QUESTION_THINKING` 并重建后端 + 验证 |
| `check_logs.sh` / `check_logs2.sh` | 抓多问检测与重生成告警 |
| `inspect-server.sh` / `inspect-keys.sh` | 服务器环境、密钥权限体检（不打印密钥值与 env 值） |
| `q_msgs.sh` / `dump_q.sh` | 导出某场会话的题目 / 全库题目（供离线分析） |

验证脚本在 `E:\hanakoWorkspace\aic83\`：`prod_smoke.py`（线上 6 轮冒烟）、
`verify_publish.py`（确认不再有 `event: delta`）、`verify_scroll2.py` / `verify_typing3.py`
（手机视口实测滚动与打字机）。

## 8. 故障速查

| 现象 | 先看 |
|---|---|
| 整站 404 | `dist` 目录是不是被删除重建过；容器日志 `docker compose logs web` |
| 首页 200 但资源 404 | `dist` 权限；`index.html` 引用的 hash 与 `assets/` 下是否一致 |
| 后端 502/健康检查失败 | `docker compose logs backend`；`.env` 改过是否重建容器 |
| 构建 OOM | `free -h`；swap 是否还在（`deploy/init-swap.sh`） |
| 流式无响应 | nginx 是否 `proxy_buffering off`；`curl -N` 直连后端看是否有事件 |
| 连不上 SSH | 用完整密钥、系统 OpenSSH；部署密钥**不能**拿 shell（正常现象） |
| 自己连不上，之前还好 | 大概率被 fail2ban 封了；换网络或控制台 VNC 登录后 unban |
| 远端脚本报 `$'\r'` | 忘了 `sed -i "s/\r$//"` |
| 远端脚本莫名少字母 r | 用了 `tr -d "\r"`，换成 `sed` |

## 9. 安全基线（2026-11-14 加固后）

**仓库是 public 的。** `deploy/` 下的文档里有服务器 IP、账号 `ubuntu`、密钥文件名，
但没有任何凭据——私钥、密码、API Key 都不在仓库里（已用 `git log -p --all` 搜过全历史，
`.env` 也被 `.gitignore` 挡着）。真正的防线是「关掉密码登录」，不是「别让人知道 IP」：
这台机器一周被尝试登录上千次，IP 早已不是秘密。

### sshd

配置文件：`/etc/ssh/sshd_config.d/99-hardening.conf`（读在 cloud-init 的 `50-cloud-init.conf` 之后）。

```
PermitRootLogin prohibit-password   # root 只能用密钥，不能用密码
PasswordAuthentication no           # 关掉密码登录
KbdInteractiveAuthentication no
PubkeyAuthentication yes
PermitEmptyPasswords no
MaxAuthTries 4
```

查看有效值（不是看配置文件，要看最终生效值）：

```bash
sudo sshd -T | grep -E "^(permitrootlogin|passwordauthentication|maxauthtries) "
```

### fail2ban

配置：`/etc/fail2ban/jail.d/sshd.local`，读 journald，**10 分钟内 5 次失败封 1 小时**。

```bash
sudo fail2ban-client status sshd          # 看失败数、当前封禁 IP
sudo fail2ban-client set sshd unbanip 1.2.3.4    # 误封了就解
sudo fail2ban-client set sshd banip 1.2.3.4      # 手动封
```

钢丝上看，封禁在 nftables 里体现为 `set addr-set-sshd { elements = { ... } }`。

> 密钥登录不会产生失败记录，所以**部署密钥（CI）不会被 fail2ban 封**。
> 反过来：如果你用错密钥连续试 5 次，自己的 IP 会被封一小时。

**被自己封了怎么办：** 换一个网络（手机热点）连，或从腾讯云控制台 VNC 登录后
`sudo fail2ban-client set sshd unbanip <你的IP>`。

### 还没做的

- 云安全组没在此文档可验证（控制台看），建议只放行 22 / 80
- `ufw` 没开（fail2ban 已足够应对 SSH 爆破，开 ufw 时注意别把 Docker 端口搞丢）

## 10. 想更省事：加一条 ssh 别名

`~/.ssh/config` 目前没有，加下面这段之后可以直接 `ssh aic`：

```
Host aic
    HostName 123.207.50.98
    User ubuntu
    IdentityFile ~/.ssh/id_ed25519_ai_coach
    IdentitiesOnly yes
```

要不要加我可以代劳，但这是改你本机的全局配置，先说一声。
