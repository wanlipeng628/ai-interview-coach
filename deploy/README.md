# 部署指南

> **现状快照（2026-10-21 核对）**
> - 系统：Ubuntu 24.04.4 LTS · 4 核 · 3.6 GiB 内存 · 40G 磁盘（已用 20%）
> - Docker 29.9.1 / Compose v5.6.0 · swap 1.9 GiB
> - 线上地址：`http://123.207.50.98`
> - 登录账号：**`ubuntu@123.207.50.98`**（不是 root），密钥 `~/.ssh/id_ed25519_ai_coach`
> - 代码目录：`/opt/ai-coach`

架构：`web`(nginx + 前端静态产物) → `backend`(FastAPI，容器内 8010) → `db`(PostgreSQL 16)。
`web` 对外暴露 80 端口；`backend` 与 `db` 只在内部网络可达。
Redis 未部署（代码里为预留，未接入业务）。

---

## 一、当前部署形态（先看这节，别急着从头搭）

线上跑的是 **预构建前端 + 服务器构建后端** 的组合：

| 服务 | 来源 | 说明 |
|---|---|---|
| `web` | `nginx:alpine` | 把 `./frontend/dist` 以只读 bind mount 挂进容器的 `/usr/share/nginx/html` |
| `backend` | `./backend` 构建 | 服务器上加镜像 |
| `db` | `postgres:16-alpine` | 数据在 `pgdata` 卷，`schema.sql` 只在首次初始化时执行 |

所以 `docker-compose.yml` 是 `docker-compose.prebuilt-web.yml` 的副本，**服务器不构建前端**。

> ⚠️ **一条硬约束**：`dist` 是 bind mount。更新时只能清空目录里的内容，
> 绝对不能 `rm -rf dist && mkdir dist` —— 容器挂的是启动那一刻的 inode，
> 删掉重建会让 nginx 指向一个已经不存在的目录，表现为整站 404。

---

## 二、日常发布：GitHub Actions 一键部署（推荐）

仓库里有一套手动触发的流水线：`.github/workflows/deploy.yml`。
在 GitHub 的 **Actions → Deploy → Run workflow** 选目标后点一下即可。

| 目标 | 做了什么 |
|---|---|
| `web` | Actions 构建前端 → 打包通过 stdin 传到服务器 → 备份旧产物 → 替换 → 重启 web → 校验首页 |
| `backend` | Actions 把源码传过去 → 覆盖 `backend/` → 重建镜像 → 重建容器 → 健康检查 |
| `all` | 上面两个都跑 |

跑完统一执行 `verify`，失败会在 Actions 里标红。

### 为什么不让服务器自己 git pull

实测这台服务器到 GitHub 的连通性不稳定（`git ls-remote` 会直接超时）。
所以后端部署改成由 Actions 把「正好那一个 commit 的源码」传过去，
比 pull 更确定，也不要求服务器能访问 GitHub。

### 部署入口是被锁死的

服务器上 `~/.ssh/authorized_keys` 里有一把 `github-actions-deploy` 专用密钥，
带 `command=` 强制命令和 `no-pty/no-port-forwarding` 等限制：
它只能执行 `web` / `backend` / `verify` / `status` 四个动作，拿不到 shell。
入口脚本是 `deploy/ci/deploy-gate.sh`，白名单就在里面。

### 需要的 Secrets（仓库 Settings → Secrets and variables → Actions）

| 名称 | 值 |
|---|---|
| `DEPLOY_HOST` | `123.207.50.98` |
| `DEPLOY_USER` | `ubuntu` |
| `DEPLOY_SSH_KEY` | 部署专用私钥全文（含 BEGIN/END 行） |

### 服务端脚本

| 文件 | 作用 |
|---|---|
| `deploy/ci/deploy-gate.sh` | 动作白名单入口 |
| `deploy/ci/web.sh` | 收 tar → 备份 → 替换 dist 内容（保留目录）→ 重启 web |
| `deploy/ci/backend.sh` | 收源码 tar → 覆盖 backend/（旧版留 `backend.prev`）→ 重建 |
| `deploy/ci/verify.sh` | 首页 + 静态资源 + 健康检查 |
| `deploy/ci/status.sh` | 当前提交、容器状态、首页资源 |

手动执行同样动作：

```bash
tar -czf - -C frontend/dist . | ssh -i <deploy_key> ubuntu@123.207.50.98 web
printf '%s\n' "$(git rev-parse HEAD)" > REVISION
tar -czf - --exclude=.venv --exclude=__pycache__ backend REVISION | ssh -i <deploy_key> ubuntu@123.207.50.98 backend
ssh -i <deploy_key> ubuntu@123.207.50.98 verify
```

---

## 三、日常发布：手动（没有 Actions 时）

### 只改了前端

```powershell
# 1. 本地构建
cd C:\Users\万里鹏\Desktop\ai-coach\ai-interview-coach\frontend
npm run build

# 2. 打包（打成 tar 比 scp -r 整个目录稳，不会出现半新半旧的中间态）
tar -czf dist.tgz -C dist .

# 3. 上传
scp -i $env:USERPROFILE\.ssh\id_ed25519_ai_coach dist.tgz ubuntu@123.207.50.98:/tmp/ai-coach-dist.tgz
```

```bash
# 4. 服务器上替换（脚本见 ai-coach-deploy/deploy-web.sh）
DIST=/opt/ai-coach/frontend/dist
cd /opt/ai-coach/frontend
cp -r "$DIST" "dist.bak-$(date +%F-%H%M)"   # 备份
find "$DIST" -mindepth 1 -delete            # 只清内容，保留目录本身
tar -xzf /tmp/ai-coach-dist.tgz -C "$DIST"
chmod -R a+rX "$DIST"                       # 权限不对会 403
cd /opt/ai-coach && sudo docker compose restart web
```

验证（拿本地 `dist/index.html` 里的 hash 对一下线上）：

```bash
curl -s http://123.207.50.98/ | grep -o 'assets/index-[^"]*'
curl -s -o /dev/null -w "%{http_code}\n" http://123.207.50.98/assets/index-XXXX.js
```

> 一键脚本：`E:\hanakoWorkspace\ai-coach-deploy\deploy-web.sh`（已含备份、替换、权限、重启、自测）。

---

## 四、日常发布：只改了后端

```bash
cd /opt/ai-coach
git pull                       # 或 scp 覆盖 backend/
sudo docker compose build backend
sudo docker compose up -d backend
free -h                        # 构建时顺手看一眼内存
```

后端有数据库结构变更时，先按第七节备份，再执行迁移语句。

---

## 五、回滚

**前端**（备份目录留着就是为这一步）：

```bash
cd /opt/ai-coach/frontend
ls -d dist.bak-*                       # 找目标备份
cp -r dist.bak-2026-10-21-2105/. dist/
sudo docker compose restart web
```

**后端**：`git log` 找到上一个提交，`git checkout <sha> -- backend/` 后重新 build；或直接 `docker compose up -d` 回退到上一版镜像（需事先给镜像打 tag，否则只能用 git 回退重建）。

---

## 六、首次上线（换新机器才需要）

**1. 开通服务器**

- 系统：Ubuntu 24.04 LTS（Server 版，无桌面）
- 安全组放行：`22`（SSH）、`80`（HTTP）

**2. 初始化**

```bash
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"        # 退出重登生效

# 国内机器加镜像加速
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json > /dev/null <<'EOF'
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.1panel.live"
  ]
}
EOF
sudo systemctl restart docker
```

**3. 加 swap**

```bash
cd /opt/ai-coach
sudo bash deploy/init-swap.sh 2G
free -h          # 应能看到 Swap: 2.0Gi
```

**4. 上传代码**

```powershell
scp -r "C:\Users\万里鹏\Desktop\ai-coach\ai-interview-coach" ubuntu@123.207.50.98:/opt/ai-coach
```

传之前删掉本地 `node_modules`、`.venv`、`frontend/dist`，否则又慢又占空间。

**5. 配置环境变量**（键名固定 9 个，值不入库）

```bash
cd /opt/ai-coach
cp .env.deploy.example .env
vim .env      # POSTGRES_PASSWORD 用强密码；LLM_API_KEY 用新生成的 Key
```

`POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DATABASE` / `LLM_PROVIDER` /
`LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` / `LLM_TEMPERATURE` / `LLM_TIMEOUT_SECONDS`

**6. 选用预构建前端形态并启动**

```bash
cd /opt/ai-coach
cp docker-compose.prebuilt-web.yml docker-compose.yml
sudo docker compose pull db
sudo docker compose build backend
sudo docker compose up -d
```

前端产物按第二节的方式上传；首次可临时在服务器构建一次，但 4 核 3.6G 上 `vue-tsc` 仍可能吃满内存，本地构建更省事。

---

## 七、运维命令

```bash
sudo docker compose ps                    # 三个服务状态
sudo docker compose logs -f backend       # 后端实时日志
sudo docker compose logs -f web           # nginx 日志
sudo docker compose restart backend
sudo docker compose down                  # 停止全部
sudo docker compose exec db psql -U interview -d interview_coach
```

健康检查：`curl http://123.207.50.98/api/v1/health` → `{"status":"ok","env":"prod"}`

---

## 八、备份数据库

```bash
sudo docker compose exec db pg_dump -U interview interview_coach > backup_$(date +%F).sql
```

---

## 九、已知差异（待整理）

1. **服务器上的 `/opt/ai-coach` 本身是一个 git 检出**，但停在 `90a9f3f`，且 `docker-compose.yml` 被就地改成了预构建版（工作区有未提交改动）。目前实际生效的是「scp 产物 + 本地改的 compose」，git 那条路只是顺带存在。
   建议后续二选一：要么彻底走 `git pull`（把 compose 变体也纳入仓库），要么彻底走 scp，避免两边打架。
2. **早期文档写的是 2 核 1G 和 root 登录**，与现状不符：机器已升到 4 核 3.6G，日常账号是 `ubuntu`。1G 时代那套「分步串行构建」的注意点仍可参考，但已不是瓶颈。
3. `frontend/dist.bak-*` 会累积，建议只保留最近两份。
