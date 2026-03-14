#!/usr/bin/env python3
"""
定时任务调度器
替代 crontab，直接在 Bot 进程中运行
"""
import os
import time
import subprocess
import threading
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/Users/mac/.openclaw/workspace/openclaw-project/runs/grid_bot/.env')

PROJECT_DIR = "/Users/mac/.openclaw/workspace/openclaw-project"
LOG_DIR = f"{PROJECT_DIR}/logs"

# 任务配置
TASKS = [
    {"name": "早间巡检", "hour": 9, "minute": 0, "script": "scripts/health_check.py", "args": ["--type", "morning", "--send"]},
    {"name": "晚间巡检", "hour": 21, "minute": 0, "script": "scripts/health_check.py", "args": ["--type", "evening", "--send"]},
]

# 检查间隔（秒）
CHECK_INTERVAL = 60

def run_task(task):
    """执行任务"""
    log_file = f"{LOG_DIR}/{task['name']}.log"
    os.makedirs(LOG_DIR, exist_ok=True)
    
    cmd = ["/usr/bin/python3", f"{PROJECT_DIR}/{task['script']}"] + task["args"]
    
    try:
        with open(log_file, "a") as f:
            f.write(f"\n=== {datetime.now().isoformat()} - {task['name']} ===\n")
            result = subprocess.run(cmd, cwd=PROJECT_DIR, capture_output=True, text=True, timeout=120)
            f.write(result.stdout)
            if result.stderr:
                f.write(f"ERROR: {result.stderr}")
            f.write(f"Exit code: {result.returncode}\n")
        print(f"✅ {task['name']} 执行完成")
    except Exception as e:
        print(f"❌ {task['name']} 执行失败: {e}")
        with open(log_file, "a") as f:
            f.write(f"ERROR: {e}\n")

def check_and_run_tasks():
    """检查并执行定时任务"""
    now = datetime.now()
    
    for task in TASKS:
        # 精确匹配：当前分钟等于任务分钟，且在最近30秒内
        if now.hour == task["hour"] and now.minute == task["minute"] and now.second < 30:
            # 避免同一分钟内重复执行
            last_run = getattr(check_and_run_tasks, "last_run", {})
            key = f"{task['name']}_{now.date()}"
            
            if last_run.get(key, "") != f"{now.hour}:{now.minute}":
                print(f"⏰ 触发 {task['name']}...")
                run_task(task)
                last_run[key] = f"{now.hour}:{now.minute}"
                check_and_run_tasks.last_run = last_run

def alert_check_loop():
    """告警检查循环 - 每15分钟"""
    while True:
        try:
            cmd = ["/usr/bin/python3", f"{PROJECT_DIR}/scripts/telegram_alert.py", "--check"]
            result = subprocess.run(cmd, cwd=PROJECT_DIR, capture_output=True, timeout=60)
            if result.returncode == 0:
                print(f"✅ 告警检查完成")
        except Exception as e:
            print(f"❌ 告警检查失败: {e}")
        time.sleep(900)  # 15分钟

def main():
    """主循环"""
    print("🚀 定时任务调度器启动")
    print(f"📁 项目目录: {PROJECT_DIR}")
    
    # 启动告警检查线程
    alert_thread = threading.Thread(target=alert_check_loop, daemon=True)
    alert_thread.start()
    print("✅ 告警检查线程已启动 (每15分钟)")
    
    # 主循环 - 每分钟检查一次
    while True:
        check_and_run_tasks()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
