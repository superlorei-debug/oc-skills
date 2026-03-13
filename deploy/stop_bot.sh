#!/bin/bash
# 停止 Bot

echo "=== Stopping Bot ==="

# 查找并停止 bot 进程
pkill -f "bot.py"

echo "Bot stopped at $(date)"
