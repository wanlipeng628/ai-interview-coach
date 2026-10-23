#!/bin/bash
# 前端发布：从 stdin 收 tar 包 -> 备份 -> 替换内容 -> 重启 web -> 自检
#
# 用法（在 CI 或本地）：tar -czf - -C frontend/dist . | ssh <host> web
#
# 关键约束：只清空 dist 目录里的内容，绝不删除目录本身。
# web 容器把 dist 以 bind mount 挂进 nginx，删掉目录重建会让容器指向已删除的 inode。
set -euo pipefail

FRONT=/opt/ai-coach/frontend
DIST="$FRONT/dist"
TS=$(date +%F-%H%M%S)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

artifact="$TMP/dist.tgz"

if [ -t 0 ]; then
  echo "没有收到产物：需要通过 stdin 传 tar，例如 tar -czf - -C dist . | ssh <host> web" >&2
  exit 2
fi
cat > "$artifact"
[ -s "$artifact" ] || { echo "产物为空" >&2; exit 2; }
tar -tzf "$artifact" > /dev/null 2>&1 || { echo "产物不是合法的 tar.gz" >&2; exit 2; }

cd "$FRONT"
# 只保留最近两份备份，避免把磁盘堆满
ls -1dt dist.bak-* 2>/dev/null | tail -n +3 | xargs -r rm -rf
cp -r "$DIST" "dist.bak-$TS"
echo "已备份到 dist.bak-$TS"

find "$DIST" -mindepth 1 -delete
tar -xzf "$artifact" -C "$DIST"
chmod -R a+rX "$DIST"
echo "已替换产物："
ls -1 "$DIST/assets"

cd /opt/ai-coach
docker compose restart web >/dev/null
sleep 2

code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 http://127.0.0.1/)
echo "index=$code"
if [ "$code" != "200" ]; then
  echo "部署失败：首页返回 $code，可用 dist.bak-$TS 回滚" >&2
  exit 1
fi
