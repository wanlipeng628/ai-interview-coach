#!/bin/bash
# 发布后自检：首页、当前引用的 js 资源、后端健康检查
set -euo pipefail

base=http://127.0.0.1

index_code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$base/")
asset=$(curl -s --max-time 10 "$base/" | grep -o 'assets/index-[^"]*\.js' | head -1)
if [ -z "$asset" ]; then
  echo "首页里找不到 js 资源引用" >&2
  exit 1
fi
asset_code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$base/$asset")
health=$(curl -s --max-time 10 "$base/api/v1/health")

echo "index=$index_code"
echo "asset=$asset ($asset_code)"
echo "health=$health"

[ "$index_code" = "200" ] || { echo "首页异常" >&2; exit 1; }
[ "$asset_code" = "200" ] || { echo "静态资源异常" >&2; exit 1; }
echo "$health" | grep -q '"status":"ok"' || { echo "后端健康检查异常" >&2; exit 1; }
echo "OK"
