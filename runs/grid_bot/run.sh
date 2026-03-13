#!/usr/bin/env python3
"""
Grid Bot 启动脚本
统一入口，确保从主工程目录运行
"""
import os
import sys
import subprocess

# 确保从正确的目录运行
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

# 启动 bot
print(f"Starting Grid Bot from: {SCRIPT_DIR}")
print(f"Python: {sys.version}")

# 执行 bot
os.execv(sys.executable, [sys.executable, "bot.py"])
