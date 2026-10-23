#!/bin/bash
# 查看线上当前状态：提交号、容器状态、首页引用的资源
set -euo pipefail

cd /opt/ai-coach
echo "== 部署版本（REVISION）=="
cat REVISION 2>/dev/null || echo "未记录（旧部署）"

echo
echo "== 容器 =="
docker compose ps

echo
echo "== 首页资源 =="
curl -s --max-time 10 http://127.0.0.1/ | grep -o 'assets/index-[^"]*' || true

echo
echo "== 后端健康 =="
curl -s --max-time 10 http://127.0.0.1/api/v1/health || true
echo
