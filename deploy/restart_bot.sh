#!/bin/bash
# 重启 Bot

RUN_DIR="/Users/mac/.openclaw/workspace/openclaw-project/runs/grid_bot"

echo "=== Restarting Bot ==="

# 停止
bash /Users/mac/.openclaw/workspace/openclaw-project/deploy/stop_bot.sh

sleep 2

# 启动
cd "$RUN_DIR"
exec python3 bot.py &

echo "Bot restarted at $(date)"
