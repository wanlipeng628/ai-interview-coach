#!/bin/bash
# 后端发布：从 stdin 收源码 tar -> 覆盖 backend/ -> 重建镜像 -> 重建容器 -> 健康检查
#
# 为什么不在这里 git pull：这台服务器到 GitHub 的连通性不稳定（实测 git ls-remote 会超时）。
# 由 Actions 把「正好那一个 commit 的源码」传过来，比 pull 更确定，也不依赖服务器出网访问 GitHub。
#
# 用法：tar -czf - backend REVISION | ssh <host> backend
set -euo pipefail

ROOT=/opt/ai-coach
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
artifact="$TMP/src.tgz"

if [ -t 0 ]; then
  echo "没有收到源码：需要 tar -czf - backend REVISION | ssh <host> backend" >&2
  exit 2
fi
cat > "$artifact"
[ -s "$artifact" ] || { echo "源码包为空" >&2; exit 2; }
tar -tzf "$artifact" > /dev/null 2>&1 || { echo "源码包不是合法的 tar.gz" >&2; exit 2; }

tar -xzf "$artifact" -C "$TMP"
[ -d "$TMP/backend" ] || { echo "源码包里没有 backend/ 目录" >&2; exit 2; }

rev=$(cat "$TMP/REVISION" 2>/dev/null || echo unknown)
echo "部署版本：$rev"

# 覆盖前留一份旧代码，便于回滚
rm -rf "$ROOT/backend.prev"
cp -r "$ROOT/backend" "$ROOT/backend.prev"

rm -rf "$ROOT/backend"
cp -r "$TMP/backend" "$ROOT/backend"
echo "$rev" > "$ROOT/REVISION"

cd "$ROOT"

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
  echo "部署失败：健康检查返回 $code（旧代码在 $ROOT/backend.prev）" >&2
  exit 1
fi
