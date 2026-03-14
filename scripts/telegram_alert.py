#!/usr/bin/env python3
"""
Telegram Alert Manager - 异常主动告警 + 恢复通知
实现三类消息：
1. 定时巡检 (health_check.py)
2. 异常主动告警
3. 恢复通知
"""
import json
import os
import time
import requests
from datetime import datetime
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv
load_dotenv('/Users/mac/.openclaw/workspace/openclaw-project/runs/grid_bot/.env')

# 路径配置
PROJECT_DIR = "/Users/mac/.openclaw/workspace/openclaw-project"
DATA_DIR = f"{PROJECT_DIR}/data/latest"
STATUS_FILE = f"{DATA_DIR}/commander_status.json"
STATE_FILE = f"{PROJECT_DIR}/runs/grid_bot/state_v2.json"

# 告警状态文件
ALERT_STATE_FILE = f"{DATA_DIR}/alert_state.json"

# Telegram 配置
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# 告警冷却时间 (秒)
ALERT_COOLDOWN = 3600  # 1小时内不重复告警
RECOVERY_COOLDOWN = 1800  # 30分钟内不重复恢复通知

# Dashboard 数据健康检查
DASHBOARD_DATA_MAX_AGE = 300  # 数据最大5分钟未更新


def load_alert_state():
    """加载告警状态"""
    if os.path.exists(ALERT_STATE_FILE):
        try:
            with open(ALERT_STATE_FILE) as f:
                return json.load(f)
        except:
            pass
    return {
        "last_alert": {},
        "last_recovery": {},
        "previous_state": {}
    }


def save_alert_state(state):
    """保存告警状态"""
    with open(ALERT_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def send_telegram(message):
    """发送到 Telegram"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram 配置缺失")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        resp = requests.post(url, json=data, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"Telegram 推送失败: {e}")
        return False


def load_current_status():
    """加载当前状态"""
    if not os.path.exists(STATUS_FILE):
        return None
    
    try:
        with open(STATUS_FILE) as f:
            return json.load(f)
    except:
        return None


def check_dashboard_health():
    """检查 Dashboard 数据健康状态"""
    issues = []
    now = time.time()
    
    # 需要检查的关键文件
    required_files = [
        "commander_status.json",
        "quant_report.json",
        "news_report.json",
        "macro_report.json"
    ]
    
    for filename in required_files:
        filepath = f"{DATA_DIR}/{filename}"
        
        # 检查文件是否存在
        if not os.path.exists(filepath):
            issues.append(f"{filename} 不存在")
            continue
        
        # 检查文件是否过期 (超过5分钟)
        mtime = os.path.getmtime(filepath)
        age_seconds = now - mtime
        
        if age_seconds > DASHBOARD_DATA_MAX_AGE:
            age_min = int(age_seconds / 60)
            issues.append(f"{filename} 已过期 ({age_min}分钟)")
    
    return issues if issues else None


def check_and_alert():
    """检查状态并发送告警/恢复通知"""
    alert_state = load_alert_state()
    current = load_current_status()
    
    if not current:
        print("无法加载状态文件")
        return
    
    now = time.time()
    
    # 提取关键状态
    overall = current.get("overall_status", "unknown")
    runtime = current.get("runtime", {})
    system = current.get("system", {})
    quant = current.get("quant", {})
    
    target_mode = runtime.get("target_mode", "")
    actual_mode = runtime.get("actual_mode", "")
    degrade_reason = runtime.get("degrade_reason", "")
    demo_connected = system.get("demo_api", {}).get("connected", True)
    can_trade = quant.get("data_validity", False)
    data_validity = quant.get("data_validity", False)
    
    # 构建当前状态签名
    state_signature = f"{overall}|{target_mode}|{actual_mode}|{demo_connected}|{can_trade}"
    
    # 检查是否有显著状态变化
    prev_state = alert_state.get("previous_state", {})
    prev_signature = f"{prev_state.get('overall', '')}|{prev_state.get('target_mode', '')}|{prev_state.get('actual_mode', '')}|{prev_state.get('demo_connected', True)}|{prev_state.get('can_trade', False)}"
    
    # ==================== 1. 核心系统告警 ====================
    alert_conditions = []
    
    # Bot 进程检查
    bot_running = system.get("bot", {}).get("running", False)
    if not bot_running:
        alert_conditions.append({
            "type": "bot_stopped",
            "title": "Bot 进程停止",
            "severity": "critical"
        })
    
    # Demo API 异常
    if not demo_connected:
        alert_conditions.append({
            "type": "demo_api_down",
            "title": "Demo API 异常",
            "severity": "critical"
        })
    
    # 系统降级
    if target_mode == "binance_demo" and actual_mode == "paper":
        alert_conditions.append({
            "type": "degraded",
            "title": "系统降级到 paper",
            "severity": "critical"
        })
    
    # can_trade = false
    if not can_trade and demo_connected:
        alert_conditions.append({
            "type": "cant_trade",
            "title": "禁止交易",
            "severity": "warning"
        })
    
    # 数据失效
    if not data_validity:
        alert_conditions.append({
            "type": "data_invalid",
            "title": "量化数据失效",
            "severity": "warning"
        })
    
    # ==================== 2. Dashboard 数据健康检查 ====================
    dashboard_issues = check_dashboard_health()
    if dashboard_issues:
        alert_conditions.append({
            "type": "dashboard_data_issue",
            "title": "Dashboard 数据异常",
            "severity": "warning",
            "details": dashboard_issues
        })
    
    # 2. 发送告警
    for condition in alert_conditions:
        alert_key = condition["type"]
        last_alert_time = alert_state.get("last_alert", {}).get(alert_key, 0)
        
        # 检查冷却时间
        if now - last_alert_time < ALERT_COOLDOWN:
            continue  # 冷却中，不重复告警
        
        # 发送告警
        message = format_alert_message(condition, current)
        if send_telegram(message):
            print(f"已发送告警: {condition['title']}")
            alert_state["last_alert"][alert_key] = now
    
    # 3. 检查恢复通知
    recovery_conditions = []
    
    # 检查是否从异常恢复到正常
    prev_can_trade = prev_state.get("can_trade", False)
    prev_demo_connected = prev_state.get("demo_connected", True)
    prev_actual_mode = prev_state.get("actual_mode", "")
    
    # Demo API 恢复
    if not prev_demo_connected and demo_connected:
        recovery_conditions.append({
            "type": "demo_api_recovered",
            "title": "Demo API 已恢复"
        })
    
    # 恢复交易
    if not prev_can_trade and can_trade:
        recovery_conditions.append({
            "type": "can_trade_recovered",
            "title": "已恢复交易能力"
        })
    
    # 恢复降级
    if target_mode == "binance_demo" and prev_actual_mode == "paper" and actual_mode == "binance_demo":
        recovery_conditions.append({
            "type": "degrade_recovered",
            "title": "已恢复到 binance_demo"
        })
    
    # 数据恢复
    if not prev_state.get("data_validity", False) and data_validity:
        recovery_conditions.append({
            "type": "data_recovered",
            "title": "量化数据已恢复"
        })
    
    # Dashboard 数据恢复
    prev_dashboard_issue = prev_state.get("dashboard_issue", False)
    current_dashboard_issues = check_dashboard_health()
    if prev_dashboard_issue and not current_dashboard_issues:
        recovery_conditions.append({
            "type": "dashboard_recovered",
            "title": "Dashboard 数据已恢复"
        })
    
    # 发送恢复通知
    for condition in recovery_conditions:
        recovery_key = condition["type"]
        last_recovery_time = alert_state.get("last_recovery", {}).get(recovery_key, 0)
        
        if now - last_recovery_time < RECOVERY_COOLDOWN:
            continue
        
        message = format_recovery_message(condition, current)
        if send_telegram(message):
            print(f"已发送恢复通知: {condition['title']}")
            alert_state["last_recovery"][recovery_key] = now
    
    # 更新状态
    alert_state["previous_state"] = {
        "overall": overall,
        "target_mode": target_mode,
        "actual_mode": actual_mode,
        "demo_connected": demo_connected,
        "can_trade": can_trade,
        "data_validity": data_validity,
        "dashboard_issue": bool(dashboard_issues)
    }
    save_alert_state(alert_state)


def format_alert_message(condition, status):
    """格式化告警消息"""
    runtime = status.get("runtime", {})
    system = status.get("system", {})
    quant = status.get("quant", {})
    
    target_mode = runtime.get("target_mode", "N/A")
    actual_mode = runtime.get("actual_mode", "N/A")
    degrade_reason = runtime.get("degrade_reason", "无")
    can_trade = quant.get("data_validity", False)
    demo_connected = system.get("demo_api", {}).get("connected", True)
    
    lines = []
    lines.append("【AI Quant Brain｜异常告警】")
    lines.append(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append(f"异常类型：{condition['title']}")
    
    # Dashboard 数据异常特殊处理
    if condition.get("type") == "dashboard_data_issue":
        lines.append(f"当前状态：数据异常")
        lines.append("")
        lines.append("影响：")
        lines.append("- Dashboard 页面可能显示大量 '-'")
        lines.append("- 看板数据可能失真")
        lines.append("")
        lines.append("检查项：")
        for detail in condition.get("details", []):
            lines.append(f"- {detail}")
        lines.append("")
        lines.append("建议动作：")
        lines.append("1. 检查 data/latest/ 目录文件是否存在")
        lines.append("2. 检查文件更新时间")
        lines.append("3. 检查 Bot 是否在运行")
        lines.append("4. 刷新 Dashboard 页面")
        return "\n".join(lines)
    
    lines.append(f"当前状态：降级运行" if actual_mode == "paper" else "当前状态：异常")
    lines.append(f"目标模式：{target_mode}")
    lines.append(f"实际模式：{actual_mode}")
    lines.append(f"can_trade：{'true' if can_trade else 'false'}")
    lines.append(f"降级原因：{degrade_reason}")
    lines.append("")
    lines.append("影响：")
    
    if not demo_connected:
        lines.append("- Demo API 连接异常")
    if actual_mode == "paper":
        lines.append("- 当前禁止做 Demo 单")
    if not can_trade:
        lines.append("- 当前不要依据量化数据做交易判断")
    
    lines.append("")
    lines.append("建议动作：")
    lines.append("1. 检查 Demo API 状态")
    lines.append("2. 检查 quant_report 是否失效")
    lines.append("3. 确认 Dashboard 是否正确显示状态")
    
    return "\n".join(lines)


def format_recovery_message(condition, status):
    """格式化恢复消息"""
    runtime = status.get("runtime", {})
    system = status.get("system", {})
    quant = status.get("quant", {})
    
    target_mode = runtime.get("target_mode", "N/A")
    actual_mode = runtime.get("actual_mode", "N/A")
    can_trade = quant.get("data_validity", False)
    overall = status.get("overall_status", "unknown")
    demo_connected = system.get("demo_api", {}).get("connected", True)
    
    lines = []
    lines.append("【AI Quant Brain｜恢复通知】")
    lines.append(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append(f"恢复项目：{condition['title']}")
    
    # Dashboard 恢复特殊处理
    if condition.get("type") == "dashboard_recovered":
        lines.append(f"当前状态：正常运行")
        lines.append("")
        lines.append("说明：")
        lines.append("- Dashboard 数据已恢复正常")
        lines.append("- 页面应显示最新数据")
        lines.append("- 不再有 '-' 出现")
        return "\n".join(lines)
    
    lines.append(f"当前状态：正常运行")
    lines.append(f"目标模式：{target_mode}")
    lines.append(f"实际模式：{actual_mode}")
    lines.append(f"can_trade：{'true' if can_trade else 'false'}")
    lines.append(f"quant 数据：{'有效' if quant.get('data_validity') else '无效'}")
    lines.append(f"overall_status：{overall}")
    lines.append("")
    lines.append("说明：")
    
    if actual_mode == "binance_demo":
        lines.append("- 系统已恢复正常 Demo 运行链")
    if can_trade:
        lines.append("- 当前已恢复交易能力")
    if demo_connected:
        lines.append("- Demo API 已恢复正常")
    
    return "\n".join(lines)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Telegram 告警检查")
    parser.add_argument("--check", action="store_true", help="执行异常检查")
    parser.add_argument("--test-alert", action="store_true", help="测试告警消息")
    parser.add_argument("--test-recovery", action="store_true", help="测试恢复消息")
    parser.add_argument("--test-dashboard-alert", action="store_true", help="测试 Dashboard 告警消息")
    parser.add_argument("--test-dashboard-recovery", action="store_true", help="测试 Dashboard 恢复消息")
    
    args = parser.parse_args()
    
    if args.test_alert:
        # 测试告警
        test_status = {
            "overall_status": "degraded",
            "runtime": {
                "target_mode": "binance_demo",
                "actual_mode": "paper",
                "degrade_reason": "Demo API 502"
            },
            "system": {
                "bot": {"running": True},
                "demo_api": {"connected": False}
            },
            "quant": {"data_validity": False}
        }
        message = format_alert_message({"title": "Demo API 异常", "type": "demo_api_down"}, test_status)
        print(message)
        if args.test_alert and "--send" in sys.argv:
            send_telegram(message)
    
    elif args.test_recovery:
        # 测试恢复
        test_status = {
            "overall_status": "ok",
            "runtime": {
                "target_mode": "binance_demo",
                "actual_mode": "binance_demo"
            },
            "system": {
                "bot": {"running": True},
                "demo_api": {"connected": True}
            },
            "quant": {"data_validity": True}
        }
        message = format_recovery_message({"title": "Demo API 已恢复", "type": "demo_api_recovered"}, test_status)
        print(message)
    
    elif args.test_dashboard_alert:
        # 测试 Dashboard 告警
        test_status = {
            "overall_status": "warning",
            "runtime": {
                "target_mode": "binance_demo",
                "actual_mode": "binance_demo",
                "degrade_reason": None
            },
            "system": {
                "bot": {"running": True},
                "demo_api": {"connected": True}
            },
            "quant": {"data_validity": True}
        }
        message = format_alert_message({
            "title": "Dashboard 数据异常",
            "type": "dashboard_data_issue",
            "details": ["quant_report.json 已过期 (32分钟)", "news_report.json 不存在"]
        }, test_status)
        print(message)
    
    elif args.test_dashboard_recovery:
        # 测试 Dashboard 恢复
        test_status = {
            "overall_status": "ok",
            "runtime": {
                "target_mode": "binance_demo",
                "actual_mode": "binance_demo"
            },
            "system": {
                "bot": {"running": True},
                "demo_api": {"connected": True}
            },
            "quant": {"data_validity": True}
        }
        message = format_recovery_message({"title": "Dashboard 数据已恢复", "type": "dashboard_recovered"}, test_status)
        print(message)
    
    elif args.check:
        # 执行检查
        check_and_alert()
    
    else:
        print("用法:")
        print("  --check         执行异常检查")
        print("  --test-alert    测试告警消息")
        print("  --test-recovery 测试恢复消息")


if __name__ == "__main__":
    import sys
    main()
