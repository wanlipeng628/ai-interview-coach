#!/bin/bash
# 后端发布：从 stdin 收源码 tar -> 覆盖 backend/ -> 重建镜像 -> 重建容器 -> 健康检查
#
# 为什么不在这里 git pull：这台服务器到 GitHub 的连通性不稳定（实测 git ls-remote 会超时）。
# 由 Actions 把「正好那一个 commit 的源码」传过来，比 pull 更确定，也不依赖服务器出网访问 GitHub。
#
# 为什么构建要脱离会话跑：镜像构建可能几分钟（基础镜像更新时更久），
# SSH 一旦断开会把前台进程一起带走，留下「源码换了但镜像没重建」的半成品状态。
# 这里用 setsid 把构建放进独立会话，再用轮询等结果，连接断了也照常构建完。
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

echo "== 重建镜像（脱离会话，连接断了也会继续）=="
LOG=/tmp/ai-coach-build.log
RC=/tmp/ai-coach-build.rc
rm -f "$RC"
: > "$LOG"
setsid bash -c "cd $ROOT && docker compose build backend > $LOG 2>&1; echo \$? > $RC" \
  < /dev/null > /dev/null 2>&1 &

while [ ! -f "$RC" ]; do
  sleep 15
  echo "  构建中… $(date +%H:%M:%S) | $(tail -n 1 "$LOG" 2>/dev/null | cut -c1-90)"
done

rc=$(cat "$RC")
if [ "$rc" != "0" ]; then
  echo "构建失败（exit=$rc），日志尾部：" >&2
  tail -n 30 "$LOG" >&2
  exit 1
fi
echo "镜像构建完成"

echo "== 重建容器 =="
docker compose up -d backend
sleep 3
docker compose ps

echo "== 健康检查 =="
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 http://127.0.0.1/api/v1/health)
echo "health=$code"
if [ "$code" != "200" ]; then
  echo "部署失败：健康检查返回 $code（旧代码在 $ROOT/backend.prev）" >&2
  exit 1
fi
