# 部署指南（2 核 1G 阿里云 ECS）

架构：`web`(nginx + 前端静态页) → `backend`(FastAPI) → `db`(PostgreSQL)
Redis 暂不部署（代码里为预留，未接入业务）。

> ⚠️ 1G 内存属于「贴着极限跑」，**swap 必须加**，构建也必须**分步串行**（见第六节）。
> 跑通后若稳定，建议后续升级到 2G，会从容很多。

---

## 一、开通服务器时选什么

- **系统**：Ubuntu 22.04 LTS（**Server 版，无桌面**）
- **安全组放行**：`22`（SSH）、`80`（HTTP）

---

## 二、服务器初始化

SSH 登录服务器后执行：

```bash
# 1. 更新系统
sudo apt update && sudo apt upgrade -y

# 2. 安装 Docker（官方脚本）
curl -fsSL https://get.docker.com | sudo sh

# 3. 当前用户加入 docker 组（退出重登后生效，或命令前加 sudo）
sudo usermod -aG docker "$USER"

# 4. 配置 Docker 国内镜像加速（国内服务器必做）
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

---

## 三、加 swap（1G 机器必做，别跳过）

```bash
# 在代码目录里执行（脚本随项目一起上传）
cd /opt/ai-coach
sudo bash deploy/init-swap.sh 2G
```

执行后应能看到 `Swap: 2.0Gi`。没加 swap 的话，构建阶段和后端运行都可能被系统 OOM Killer 杀掉。

---

## 四、上传代码

在**本地 Windows PowerShell** 里执行（把 `<公网IP>` 换成你的）：

```powershell
scp -r "C:\Users\万里鹏\Desktop\ai-coach\ai-interview-coach" root@<公网IP>:/opt/ai-coach
```

如果代码里有 `node_modules` 和 `.venv`，传输会很慢，可以先删掉再传（服务器端会重新装）。

---

## 五、配置环境变量

```bash
cd /opt/ai-coach
cp .env.deploy.example .env
vim .env     # 填写 POSTGRES_PASSWORD 和 LLM_API_KEY
```

> 两个关键点：
> 1. `POSTGRES_PASSWORD` 换成强密码，不要用默认的 `pgvector`
> 2. `LLM_API_KEY` 用**重新生成**的 Key（之前暴露过的那个请先吊销）

---

## 六、构建与启动（1G 机器：分步来，别用一条 up --build）

> ⚠️ 实测：1G 机器上 `docker compose build web` 会在 vue-tsc 阶段因内存不足 OOM（`JavaScript heap out of memory`）。
> **后端在服务器构建没问题；前端建议直接跳过服务器构建，用第九节的本地构建方案。**

1G 内存下，如果让 compose 同时构建前后端，内存峰值容易打爆。**逐个构建**：

```bash
cd /opt/ai-coach

# 1. 先拉基础镜像（db 是现成镜像，直接拉）
sudo docker compose pull db

# 2. 先构建后端（pip 装依赖）
sudo docker compose build backend

# 3. 再构建前端（npm + vite，内存最吃紧的一步）
sudo docker compose build web

# 4. 全部后台启动
sudo docker compose up -d
```

---

## 七、验证

```bash
sudo docker compose ps                # 三个服务应为 Up / healthy
sudo docker compose logs -f backend   # 观察后端启动日志
free -h                               # 看内存和 swap 使用情况
```

浏览器打开 `http://<公网IP>`，能进首页即成功。手机浏览器同样访问这个地址。

---

## 八、常用运维命令

```bash
sudo docker compose logs -f backend     # 后端实时日志
sudo docker compose logs -f web         # nginx 日志
sudo docker compose restart backend     # 重启后端
sudo docker compose down                # 停止全部
sudo docker compose up -d --build       # 改代码后重建并启动
sudo docker compose exec db psql -U interview -d interview_coach   # 进数据库
```

## 九、如果前端构建失败（1G 常见）

如果 `docker compose build web` 过程中出现 `Killed`、`JavaScript heap out of memory` 或长时间卡死，说明内存不够。用这个**本地构建**的兜底方案：

**1）本地 Windows 构建前端**

```powershell
cd C:\Users\万里鹏\Desktop\ai-coach\ai-interview-coach\frontend
npm run build
```

得到 `frontend\dist` 目录。

**2）把 dist 传到服务器（注意：上传后目录权限是 700，nginx 读不到会 403）**

```powershell
scp -r .\dist root@<公网IP>:/opt/ai-coach/frontend/dist
# 传完必须修复权限，否则 nginx 403 Forbidden
ssh root@<公网IP> "chmod -R a+rX /opt/ai-coach/frontend/dist/"
```

**3）改用预构建的 nginx 配置**

把项目里的 `docker-compose.prebuilt-web.yml` 覆盖 `docker-compose.yml`：

```bash
cd /opt/ai-coach
cp docker-compose.prebuilt-web.yml docker-compose.yml
sudo docker compose up -d
```

---

## 十、备份数据库

```bash
sudo docker compose exec db pg_dump -U interview interview_coach > backup_$(date +%F).sql
```
