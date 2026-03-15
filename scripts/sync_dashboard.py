#!/usr/bin/env python3
"""
Dashboard 数据同步脚本
将 data/latest/ 同步到 dashboard/data/latest/
"""
import shutil
import os
from datetime import datetime

SRC_DIR = "/Users/mac/.openclaw/workspace/openclaw-project/data/latest"
DST_DIR = "/Users/mac/.openclaw/workspace/openclaw-project/dashboard/data/latest"

def sync_files():
    """同步文件"""
    count = 0
    for fname in os.listdir(SRC_DIR):
        if fname.endswith('.json'):
            src = f"{SRC_DIR}/{fname}"
            dst = f"{DST_DIR}/{fname}"
            shutil.copy2(src, dst)
            count += 1
    print(f"✅ 同步完成: {count} 个文件")

if __name__ == "__main__":
    sync_files()
