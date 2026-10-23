#!/bin/bash
# GitHub Actions 专用入口。
# 由 ~/.ssh/authorized_keys 的 command= 强制调用，原始命令在 $SSH_ORIGINAL_COMMAND。
# 这把密钥只能执行下面白名单里的动作，拿不到交互式 shell，也做不了端口转发。
set -euo pipefail

action="${SSH_ORIGINAL_COMMAND:-}"

case "$action" in
  web|backend|verify|status)
    exec bash "/opt/ai-coach/deploy/ci/${action}.sh"
    ;;
  *)
    echo "refused: unsupported action '${action}'" >&2
    echo "allowed: web, backend, verify, status" >&2
    exit 1
    ;;
esac
