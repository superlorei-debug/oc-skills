#!/usr/bin/env python3
"""
Commander - 主控汇总模块 V10
统一汇总格式，固定栏目输出
"""
import subprocess
import json
import os
import sys
from datetime import datetime, timedelta

HISTORY_DIR = "data/history/commander"

# 执行状态枚举
STATUS_EXECUTED = "已执行"
STATUS_NO_UPDATE = "无更新"
STATUS_FAILED = "执行失败"
STATUS_NOT_CONNECTED = "未接入"


def detect_mode(user_input):
    """根据用户输入判断模式"""
    text = user_input.lower()
    
    # 检测详细版
    detail_keywords = ["详细版", "详细看看", "展开", "完整", "具体"]
    if any(k in text for k in detail_keywords):
        return "detail"
    
    return "simple"


def get_today_file():
    return f"{HISTORY_DIR}/{datetime.now().strftime('%Y-%m-%d')}.json"


def run_cmd(path):
    """运行脚本并返回输出"""
    try:
        r = subprocess.run(
            ["python3", path], 
            capture_output=True, 
            text=True, 
            timeout=15,
            cwd="/Users/mac/.openclaw/workspace/openclaw-project"
        )
        return r.stdout, r.stderr, r.returncode
    except Exception as e:
        return "", str(e), -1


def check_bot_status():
    """检查 Bot 运行状态"""
    import subprocess
    try:
        r = subprocess.run(
            ["ps", "aux"], 
            capture_output=True, 
            text=True
        )
        for line in r.stdout.split("\n"):
            if "bot.py" in line and "grep" not in line:
                # 提取 PID
                parts = line.split()
                if len(parts) > 1:
                    return {
                        "running": True,
                        "pid": parts[1],
                        "status": "运行中"
                    }
        return {
            "running": False,
            "pid": None,
            "status": "未运行"
        }
    except:
        return {
            "running": False,
            "pid": None,
            "status": "未知"
        }


def check_demo_api():
    """检查 Demo API 连接状态"""
    import requests
    try:
        resp = requests.get("https://demo-api.binance.com/api/v3/ping", timeout=5)
        if resp.status_code == 200:
            return {"connected": True, "status": "正常"}
    except:
        pass
    return {"connected": False, "status": "异常"}


def parse_quant():
    """解析量化模块输出"""
    out, err, code = run_cmd("scripts/quant_report.py")
    
    result = {
        "status": STATUS_NO_UPDATE,
        "status_text": "无更新",
        "price": "0",
        "balance_usdt": "0",
        "position_btc": "0",
        "layers_used": "0",
        "layers_limit": "6",
        "utilization": "0%",
        "pnl": "0",
        "orders_count": "0",
        "risk": "无",
        "action": "保持观察",
        "time": datetime.now().strftime('%H:%M'),
        "error": None,
        "data_source": "未知",
    }
    
    if code != 0 or err:
        result["status"] = STATUS_FAILED
        result["status_text"] = "执行失败"
        result["error"] = err[:100] if err else "未知错误"
        return result
    
    # 尝试解析 JSON
    try:
        # 查找 JSON 输出
        lines = out.split("\n")
        json_start = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("{"):
                json_start = i
                break
        
        if json_start >= 0:
            json_str = "\n".join(lines[json_start:])
            data = json.loads(json_str)
            
            result["status"] = STATUS_EXECUTED
            result["status_text"] = "已执行"
            result["price"] = str(data.get("price_usd", 0))
            result["balance_usdt"] = str(data.get("total_u", 0))
            result["position_btc"] = str(data.get("position_btc", 0))
            result["layers_used"] = str(data.get("inventory_layers_used", 0))
            result["layers_limit"] = str(data.get("inventory_layers_limit", 6))
            result["utilization"] = str(data.get("capital_utilization_pct", 0)) + "%"
            result["orders_count"] = str(data.get("open_orders_count", 0))
            result["data_source"] = data.get("data_source", "未知")
            
            # 状态判断
            status = data.get("status", "ok")
            if status == "critical":
                result["status_text"] = "危险"
            elif status == "warning":
                result["status_text"] = "预警"
            else:
                result["status_text"] = "正常"
            
            result["risk"] = data.get("risk_reason", "暂无")
            result["action"] = data.get("top_action", "保持观察")
            
    except Exception as e:
        result["status"] = STATUS_FAILED
        result["status_text"] = "解析失败"
        result["error"] = str(e)[:100]
    
    return result


def parse_news():
    """解析新闻模块输出"""
    out, err, code = run_cmd("scripts/news_report.py")
    
    result = {
        "status": STATUS_NOT_CONNECTED,
        "status_text": "未接入",
        "mode": "无",
        "count": "0",
        "articles": [],
        "time": datetime.now().strftime('%H:%M'),
        "error": None,
    }
    
    if code != 0 or err:
        result["status"] = STATUS_FAILED
        result["status_text"] = "执行失败"
        result["error"] = err[:100] if err else "未知错误"
        return result
    
    # 简单解析
    if "实时模式" in out:
        result["status"] = STATUS_EXECUTED
        result["status_text"] = "已执行"
        result["mode"] = "实时"
    elif "缓存模式" in out:
        result["status"] = STATUS_EXECUTED
        result["status_text"] = "已执行(缓存)"
        result["mode"] = "缓存"
    else:
        result["status"] = STATUS_NO_UPDATE
        result["status_text"] = "无更新"
        result["mode"] = "无"
    
    return result


def parse_macro():
    """解析宏观模块输出"""
    out, err, code = run_cmd("scripts/macro_report.py")
    
    result = {
        "status": STATUS_NOT_CONNECTED,
        "status_text": "未接入",
        "phase": "未知",
        "strategy": "未知",
        "advice": "暂无建议",
        "time": datetime.now().strftime('%H:%M'),
        "error": None,
    }
    
    if code != 0 or err:
        result["status"] = STATUS_FAILED
        result["status_text"] = "执行失败"
        result["error"] = err[:100] if err else "未知错误"
        return result
    
    if "当前阶段" in out:
        result["status"] = STATUS_EXECUTED
        result["status_text"] = "已执行"
        
        for line in out.split("\n"):
            if "当前阶段：" in line and "定义" not in line:
                result["phase"] = line.split("：")[-1].strip()
            elif "家庭策略：" in line and "定义" not in line:
                result["strategy"] = line.split("：")[-1].strip()
            elif "一句话建议：" in line:
                result["advice"] = line.split("：")[-1].strip()
    else:
        result["status"] = STATUS_NO_UPDATE
        result["status_text"] = "无更新"
    
    return result


def format_output(quant, news, macro, bot_status, demo_status, is_detail=False):
    """统一格式化输出"""
    
    lines = []
    
    # ========== 标题 ==========
    lines.append("=" * 60)
    lines.append("📋 今日总览")
    lines.append("=" * 60)
    lines.append(f"📅 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # ========== 一、量化交易 ==========
    lines.append("一、量化交易")
    lines.append("-" * 40)
    lines.append(f"├─ 执行状态：{quant['status_text']}")
    lines.append(f"├─ 更新时间：{quant['time']}")
    lines.append(f"├─ 数据来源：{quant['data_source']}")
    
    if quant['status'] == STATUS_EXECUTED:
        lines.append(f"├─ BTC 价格：${quant['price']}")
        lines.append(f"├─ USDT 余额：{quant['balance_usdt']}")
        lines.append(f"├─ BTC 持仓：{quant['position_btc']}")
        lines.append(f"├─ 库存层数：{quant['layers_used']}/{quant['layers_limit']}")
        lines.append(f"├─ 资金利用率：{quant['utilization']}")
        lines.append(f"├─ 挂单数量：{quant['orders_count']}单")
        lines.append(f"├─ 当前状态：{quant['status_text']}")
        lines.append(f"├─ 风险提示：{quant['risk']}")
        lines.append(f"└─ 建议动作：{quant['action']}")
    elif quant['status'] == STATUS_FAILED:
        lines.append(f"└─ ❌ 错误：{quant.get('error', '未知错误')}")
    else:
        lines.append(f"└─ 暂无数据")
    
    lines.append("")
    
    # ========== 二、新闻与地缘 ==========
    lines.append("二、新闻与地缘")
    lines.append("-" * 40)
    lines.append(f"├─ 执行状态：{news['status_text']}")
    lines.append(f"├─ 更新时间：{news['time']}")
    
    if news['status'] in [STATUS_EXECUTED, "已执行(缓存)"]:
        lines.append(f"├─ 获取模式：{news['mode']}")
        lines.append(f"└─ 新闻数量：{news['count']}条")
    elif news['status'] == STATUS_FAILED:
        lines.append(f"└─ ❌ 错误：{news.get('error', '未知错误')}")
    else:
        lines.append(f"└─ 📝 暂无新闻更新")
    
    lines.append("")
    
    # ========== 三、宏观环境 ==========
    lines.append("三、宏观环境")
    lines.append("-" * 40)
    lines.append(f"├─ 执行状态：{macro['status_text']}")
    lines.append(f"├─ 更新时间：{macro['time']}")
    
    if macro['status'] == STATUS_EXECUTED:
        lines.append(f"├─ 当前阶段：{macro['phase']}")
        lines.append(f"├─ 家庭策略：{macro['strategy']}")
        lines.append(f"└─ 一句话建议：{macro['advice']}")
    elif macro['status'] == STATUS_FAILED:
        lines.append(f"└─ ❌ 错误：{macro.get('error', '未知错误')}")
    else:
        lines.append(f"└─ 📝 暂无宏观更新")
    
    lines.append("")
    
    # ========== 四、系统状态 ==========
    lines.append("四、系统状态")
    lines.append("-" * 40)
    
    # Bot 状态
    if bot_status['running']:
        lines.append(f"├─ Bot 运行：✅ 运行中 (PID: {bot_status['pid']})")
    else:
        lines.append(f"├─ Bot 运行：❌ 未运行")
    
    # Demo API 状态
    if demo_status['connected']:
        lines.append(f"├─ Demo API：✅ {demo_status['status']}")
    else:
        lines.append(f"├─ Demo API：⚠️ {demo_status['status']} (降级运行)")
    
    # 执行模式
    exec_mode = "binance_demo"  # 从 .env 读取
    try:
        with open("/tmp/binance-spot-grid-bot/.env") as f:
            for line in f:
                if "EXECUTION_MODE=" in line:
                    exec_mode = line.split("=")[1].strip()
    except:
        pass
    
    if not demo_status['connected']:
        lines.append(f"├─ 执行模式：{exec_mode} (已降级)")
        lines.append(f"└─ ⚠️ 系统运行状态：降级运行（Demo API 异常）")
    else:
        lines.append(f"└─ 执行模式：{exec_mode}")
    
    lines.append("")
    
    # ========== 五、今日建议 ==========
    lines.append("五、今日建议")
    lines.append("-" * 40)
    
    # 综合判断
    if not demo_status['connected']:
        lines.append("├─ 总体风险：⚠️ 中等")
        lines.append("├─ 原因：Demo API 异常，Bot 已降级运行")
        lines.append("├─ 建议：")
        lines.append("│    - 关注 Demo API 恢复情况")
        lines.append("│    - 当前交易为模拟数据，非真实执行")
        lines.append("│    - 如需真实交易，请等待 API 恢复后重启")
        lines.append("└─ 后续行动：等待 Demo API 恢复")
    elif quant['status_text'] == "危险":
        lines.append("├─ 总体风险：🔴 高")
        lines.append("├─ 原因：量化模块状态危险")
        lines.append(f"└─ 建议：{quant['action']}")
    elif quant['status_text'] == "预警":
        lines.append("├─ 总体风险：🟡 中等")
        lines.append("├─ 原因：量化模块状态预警")
        lines.append(f"└─ 建议：{quant['action']}")
    else:
        lines.append("├─ 总体风险：🟢 低")
        lines.append("├─ 原因：各模块运行正常")
        lines.append("└─ 建议：保持当前节奏，继续观察")
    
    lines.append("")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def main(user_input=""):
    # 检测模式
    mode = detect_mode(user_input)
    is_detail = (mode == "detail")
    
    # 获取各模块数据
    print("🔄 正在获取数据...")
    
    quant = parse_quant()
    news = parse_news()
    macro = parse_macro()
    bot_status = check_bot_status()
    demo_status = check_demo_api()
    
    # 输出
    output = format_output(quant, news, macro, bot_status, demo_status, is_detail)
    print(output)


if __name__ == "__main__":
    user_input = sys.argv[1] if len(sys.argv) > 1 else ""
    main(user_input)
