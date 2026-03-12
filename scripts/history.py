#!/usr/bin/env python3
"""
历史对比功能
"""
import json
import os
from datetime import datetime, timedelta

HISTORY_DIR = "/tmp/commander_history"

def get_today_file():
    return f"{HISTORY_DIR}/{datetime.now().strftime('%Y-%m-%d')}.json"

def get_yesterday_file():
    yesterday = datetime.now() - timedelta(days=1)
    return f"{HISTORY_DIR}/{yesterday.strftime('%Y-%m-%d')}.json"

def save_today(data):
    os.makedirs(HISTORY_DIR, exist_ok=True)
    with open(get_today_file(), "w") as f:
        json.dump(data, f)

def load_yesterday():
    f = get_yesterday_file()
    if os.path.exists(f):
        with open(f) as f:
            return json.load(f)
    return None

def compare():
    """对比今天和昨天"""
    today_file = get_today_file()
    yesterday = load_yesterday()
    
    if not yesterday:
        return None
    
    # 读取今天数据（从量化模块）
    # 简化版：对比量化状态
    try:
        with open("/tmp/quant_today.json") as f:
            today = json.load(f)
    except:
        return None
    
    comparisons = []
    
    # 对比量化
    if yesterday.get("quant_status") and today.get("status"):
        old = yesterday.get("quant_status", "")
        new = today.get("status", "")
        if old != new:
            comparisons.append(f"量化：从{old}变到{new}")
    
    return comparisons

def save_daily_summary(quant_status, news_mode, macro_phase, overall):
    """保存每日摘要"""
    os.makedirs(HISTORY_DIR, exist_ok=True)
    
    data = {
        "date": datetime.now().strftime('%Y-%m-%d'),
        "quant_status": quant_status,
        "news_mode": news_mode,
        "macro_phase": macro_phase,
        "overall": overall,
        "timestamp": datetime.now().isoformat()
    }
    
    with open(get_today_file(), "w") as f:
        json.dump(data, f)

if __name__ == "__main__":
    # 测试
    save_daily_summary("预警", "实时模式", "弱修复", "谨慎运行")
    print("已保存今日摘要")
