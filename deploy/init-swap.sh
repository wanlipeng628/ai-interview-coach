#!/usr/bin/env bash
# 小内存服务器初始化 swap，防止内存不足时被 OOM Killer 杀进程
# 用法：sudo bash deploy/init-swap.sh [大小，默认 2G]
set -euo pipefail

SWAP_SIZE="${1:-2G}"

if swapon --show | grep -q .; then
    echo "[skip] 已存在启用的 swap："
    swapon --show
    exit 0
fi

echo "[1/5] 创建 ${SWAP_SIZE} swap 文件..."
fallocate -l "${SWAP_SIZE}" /swapfile 2>/dev/null || \
    dd if=/dev/zero of=/swapfile bs=1M count=2048 status=progress

echo "[2/5] 设置权限..."
chmod 600 /swapfile

echo "[3/5] 格式化并启用..."
mkswap /swapfile
swapon /swapfile

echo "[4/5] 写入 /etc/fstab 开机自动挂载..."
grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab

echo "[5/5] 调低 swappiness（优先用物理内存，swap 仅兜底）..."
sysctl -w vm.swappiness=10
grep -q '^vm.swappiness' /etc/sysctl.conf || echo 'vm.swappiness=10' >> /etc/sysctl.conf

echo
echo "完成。当前内存与 swap 情况："
free -h
