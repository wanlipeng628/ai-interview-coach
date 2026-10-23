#!/bin/bash
# 后端发布：拉代码 -> 重建镜像 -> 重建容器 -> 健康检查
# 依赖层在服务器上已有缓存，日常改代码只会重跑代码层（约 1 分钟）。
set -euo pipefail

cd /opt/ai-coach

echo "== 拉取代码 =="
git pull --ff-only

echo "== 重建镜像 =="
docker compose build backend

echo "== 重建容器 =="
docker compose up -d backend
sleep 3
docker compose ps --format 'table {{.Service}}\t{{.Status}}'

echo "== 健康检查 =="
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 http://127.0.0.1/api/v1/health)
echo "health=$code"
if [ "$code" != "200" ]; then
  echo "部署失败：健康检查返回 $code" >&2
  exit 1
fi
