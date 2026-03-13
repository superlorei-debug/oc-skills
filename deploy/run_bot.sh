#!/bin/bash
# 运行 Bot - 单源运行版本

PROJECT_DIR="/Users/mac/.openclaw/workspace/openclaw-project"
RUN_DIR="$PROJECT_DIR/runs/grid_bot"

echo "=== AI Quant Brain Bot Launcher ==="
echo "Project: $PROJECT_DIR"
echo "Run Dir: $RUN_DIR"
echo "Time: $(date)"

cd "$RUN_DIR"

# 检查符号链接
if [ -L "bot.py" ]; then
    echo "Code Source: $(readlink bot.py)"
else
    echo "ERROR: bot.py is not a symlink!"
    exit 1
fi

# 检查配置文件
if [ ! -f ".env" ]; then
    echo "ERROR: .env not found!"
    exit 1
fi

# 启动
echo "Starting bot..."
exec python3 bot.py
