#!/usr/bin/env python3
"""
Commander - 主控汇总模块 V11
统一汇总格式，固定栏目输出，数据语义完善
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
STATUS_DEGRADED = "降级运行"

# 缺失值标记
VAL_NA = "N/A"
VAL_FAILED = "获取失败"
VAL_USING_CACHE = "使用缓存"


def detect_mode(user_input):
    """根据用户输入判断模式"""
    text = user_input.lower()
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
        r = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        for line in r.stdout.split("\n"):
            if "bot.py" in line and "grep" not in line:
                parts = line.split()
                if len(parts) > 1:
                    return {"running": True, "pid": parts[1], "status": "运行中"}
        return {"running": False, "pid": None, "status": "未运行"}
    except:
        return {"running": False, "pid": None, "status": "未知"}


def get_exec_mode():
    """获取执行模式"""
    try:
        with open("/tmp/binance-spot-grid-bot/.env") as f:
            for line in f:
                if "EXECUTION_MODE=" in line:
                    return line.split("=")[1].strip()
    except:
        pass
    return VAL_NA


def check_demo_api():
    """检查 Demo API 连接状态"""
    import requests
    try:
        resp = requests.get("https://demo-api.binance.com/api/v3/ping", timeout=5)
        if resp.status_code == 200:
            return {"connected": True, "status": "正常", "latency_ms": resp.elapsed.total_seconds() * 1000}
    except Exception as e:
        return {"connected": False, "status": str(e)[:30], "latency_ms": 0}
    return {"connected": False, "status": "未知", "latency_ms": 0}


def parse_quant():
    """解析量化模块输出"""
    out, err, code = run_cmd("scripts/quant_report.py")
    
    result = {
        "exec_status": STATUS_FAILED,           # 模块执行状态
        "run_mode": VAL_NA,                    # 当前实际运行模式
        "data_status": VAL_FAILED,              # 数据获取状态
        "data_valid": False,                    # 数据是否有效
        "price": VAL_FAILED,
        "balance_usdt": VAL_FAILED,
        "position_btc": VAL_FAILED,
        "layers_used": VAL_NA,
        "layers_limit": "6",
        "utilization": VAL_NA,
        "pnl": VAL_NA,
        "orders_count": VAL_NA,
        "risk": VAL_NA,
        "action": VAL_NA,
        "time": datetime.now().strftime('%H:%M'),
        "last_success_time": VAL_NA,
        "data_source": VAL_FAILED,
        "error": None,
    }
    
    # 获取执行模式
    result["run_mode"] = get_exec_mode()
    
    # 检查 Demo API
    demo_status = check_demo_api()
    
    # 解析 JSON
    try:
        lines = out.split("\n")
        json_start = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("{"):
                json_start = i
                break
        
        if json_start >= 0:
            json_str = "\n".join(lines[json_start:])
            data = json.loads(json_str)
            
            # 检查数据是否有效（价格>0 表示成功）
            price_val = data.get("price_usd", 0)
            balance_val = data.get("total_u", 0)
            
            if price_val and price_val > 0:
                result["data_valid"] = True
                result["data_status"] = "已获取"
                result["exec_status"] = STATUS_EXECUTED
                
                result["price"] = f"${price_val:,.2f}"
                result["balance_usdt"] = str(balance_val)
                result["position_btc"] = str(data.get("position_btc", 0))
                result["layers_used"] = str(data.get("inventory_layers_used", 0))
                result["layers_limit"] = str(data.get("inventory_layers_limit", 6))
                result["utilization"] = str(data.get("capital_utilization_pct", 0)) + "%"
                result["orders_count"] = str(data.get("open_orders_count", 0))
                result["data_source"] = data.get("data_source", "未知")
                result["last_success_time"] = data.get("updated_at", VAL_NA)
                
                # 状态判断
                status = data.get("status", "ok")
                if status == "critical":
                    result["risk"] = "🔴 危险 - " + (data.get("risk_reason", "库存已打满")[:30])
                    result["action"] = data.get("top_action", "立即暂停新开仓")
                elif status == "warning":
                    result["risk"] = "🟡 预警 - " + (data.get("risk_reason", "接近上限")[:30])
                    result["action"] = data.get("top_action", "关注加仓节奏")
                else:
                    result["risk"] = "🟢 正常"
                    result["action"] = data.get("top_action", "保持观察")
            else:
                # 数据无效
                if not demo_status["connected"]:
                    result["data_status"] = "Demo API 异常"
                    result["exec_status"] = STATUS_DEGRADED
                    result["data_source"] = "降级运行（Demo API 502）"
                else:
                    result["data_status"] = "数据为空"
                    
    except Exception as e:
        result["error"] = str(e)[:100]
        result["data_status"] = "解析失败"
    
    return result


def parse_news():
    """解析新闻模块输出"""
    out, err, code = run_cmd("scripts/news_report.py")
    
    result = {
        "exec_status": STATUS_NOT_CONNECTED,
        "mode": VAL_NA,
        "count": VAL_NA,
        "articles": [],
        "time": datetime.now().strftime('%H:%M'),
        "last_success_time": VAL_NA,
        "error": None,
    }
    
    if code != 0 or err:
        result["exec_status"] = STATUS_FAILED
        result["error"] = err[:100] if err else "未知错误"
        return result
    
    if "实时模式" in out:
        result["exec_status"] = STATUS_EXECUTED
        result["mode"] = "实时"
    elif "缓存模式" in out:
        result["exec_status"] = STATUS_EXECUTED
        result["mode"] = VAL_USING_CACHE
    else:
        result["exec_status"] = STATUS_NO_UPDATE
    
    return result


def parse_macro():
    """解析宏观模块输出"""
    out, err, code = run_cmd("scripts/macro_report.py")
    
    result = {
        "exec_status": STATUS_NOT_CONNECTED,
        "phase": VAL_NA,
        "strategy": VAL_NA,
        "advice": VAL_NA,
        "time": datetime.now().strftime('%H:%M'),
        "last_success_time": VAL_NA,
        "error": None,
    }
    
    if code != 0 or err:
        result["exec_status"] = STATUS_FAILED
        result["error"] = err[:100] if err else "未知错误"
        return result
    
    if "当前阶段" in out:
        result["exec_status"] = STATUS_EXECUTED
        for line in out.split("\n"):
            if "当前阶段：" in line and "定义" not in line:
                result["phase"] = line.split("：")[-1].strip()
            elif "家庭策略：" in line and "定义" not in line:
                result["strategy"] = line.split("：")[-1].strip()
            elif "一句话建议：" in line:
                result["advice"] = line.split("：")[-1].strip()
    else:
        result["exec_status"] = STATUS_NO_UPDATE
    
    return result


def format_output(quant, news, macro, bot_status, demo_status):
    """统一格式化输出"""
    
    lines = []
    
    # ========== 标题 ==========
    lines.append("=" * 60)
    lines.append("📋 今日总览")
    lines.append("=" * 60)
    lines.append(f"📅 报告时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # ========== 一、量化交易 ==========
    lines.append("一、量化交易")
    lines.append("-" * 40)
    
    # 模块执行状态
    lines.append(f"├─ 模块执行状态：{quant['exec_status']}")
    
    # 实际运行模式
    if quant['exec_status'] == STATUS_DEGRADED:
        target_mode = "binance_demo"
        lines.append(f"├─ 目标运行模式：binance_demo")
        lines.append(f"├─ 当前实际模式：paper (降级)")
        lines.append(f"├─ 降级原因：Demo API 502 Bad Gateway")
    else:
        lines.append(f"├─ 当前运行模式：{quant['run_mode']}")
    
    # 数据获取状态
    lines.append(f"├─ 数据获取状态：{quant['data_status']}")
    
    # 数据有效性
    if quant['data_valid']:
        lines.append(f"├─ 数据有效性：✅ 有效")
    else:
        lines.append(f"├─ 数据有效性：❌ 无效")
    
    # 详细数据（仅在有效时显示）
    if quant['data_valid']:
        lines.append(f"├─ BTC 价格：{quant['price']}")
        lines.append(f"├─ USDT 余额：{quant['balance_usdt']}")
        lines.append(f"├─ BTC 持仓：{quant['position_btc']}")
        lines.append(f"├─ 库存层数：{quant['layers_used']}/{quant['layers_limit']}")
        lines.append(f"├─ 资金利用率：{quant['utilization']}")
        lines.append(f"├─ 挂单数量：{quant['orders_count']}单")
        lines.append(f"├─ 当前状态：{quant['risk']}")
        lines.append(f"├─ 风险提示：{quant['risk']}")
        lines.append(f"└─ 建议动作：{quant['action']}")
    else:
        # 数据无效时的占位显示
        lines.append(f"├─ BTC 价格：{quant['price']}")
        lines.append(f"├─ USDT 余额：{quant['balance_usdt']}")
        lines.append(f"├─ BTC 持仓：{quant['position_btc']}")
        lines.append(f"├─ 库存层数：{quant['layers_used']}")
        lines.append(f"├─ 资金利用率：{quant['utilization']}")
        lines.append(f"├─ 挂单数量：{quant['orders_count']}")
        lines.append(f"├─ 当前状态：❌ 数据获取失败")
        lines.append(f"├─ 风险提示：无法评估")
        lines.append(f"└─ 建议动作：检查 Demo API 连接")
    
    # 最后成功同步时间
    if quant['last_success_time'] != VAL_NA:
        lines.append(f"└─ 最后成功同步：{quant['last_success_time']}")
    else:
        lines.append(f"└─ 最后成功同步：N/A")
    
    lines.append("")
    
    # ========== 二、新闻与地缘 ==========
    lines.append("二、新闻与地缘")
    lines.append("-" * 40)
    lines.append(f"├─ 模块执行状态：{news['exec_status']}")
    
    if news['exec_status'] == STATUS_EXECUTED:
        lines.append(f"├─ 获取模式：{news['mode']}")
        lines.append(f"├─ 新闻数量：{news['count']}")
        lines.append(f"└─ 最后更新：{news['time']}")
    elif news['exec_status'] == STATUS_NO_UPDATE:
        lines.append(f"├─ 获取模式：{news['mode']}")
        lines.append(f"└─ 📝 暂无新闻更新")
    else:
        lines.append(f"└─ ❌ {news.get('error', '执行失败')}")
    
    lines.append("")
    
    # ========== 三、宏观环境 ==========
    lines.append("三、宏观环境")
    lines.append("-" * 40)
    lines.append(f"├─ 模块执行状态：{macro['exec_status']}")
    
    if macro['exec_status'] == STATUS_EXECUTED:
        lines.append(f"├─ 当前阶段：{macro['phase']}")
        lines.append(f"├─ 家庭策略：{macro['strategy']}")
        lines.append(f"└─ 一句话建议：{macro['advice']}")
    elif macro['exec_status'] == STATUS_NO_UPDATE:
        lines.append(f"└─ 📝 暂无宏观更新")
    else:
        lines.append(f"└─ ❌ {macro.get('error', '执行失败')}")
    
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
        lines.append(f"├─ Demo API：✅ 正常")
    else:
        lines.append(f"├─ Demo API：❌ 异常 ({demo_status['status']})")
    
    # 执行模式
    exec_mode = get_exec_mode()
    if not demo_status['connected']:
        lines.append(f"├─ 目标执行模式：binance_demo")
        lines.append(f"├─ 当前执行模式：paper (降级)")
        lines.append(f"└─ ⚠️ 系统状态：降级运行")
    else:
        lines.append(f"└─ 执行模式：{exec_mode}")
    
    lines.append("")
    
    # ========== 五、今日建议 ==========
    lines.append("五、今日建议")
    lines.append("-" * 40)
    
    # 根据状态给出具体建议
    if not demo_status['connected']:
        lines.append("├─ 总体风险：⚠️ 需关注")
        lines.append("├─ 原因：Demo API 异常，系统降级运行")
        lines.append("├─ 可执行动作：")
        lines.append("│    1. 暂不依据当前 Demo 数据做交易判断")
        lines.append("│    2. 检查 Demo API 恢复情况")
        lines.append("│    3. 检查 Dashboard 是否正确显示降级状态")
        lines.append("│    4. 恢复后重新校验余额、价格、订单同步")
        lines.append("└─ 后续行动：等待 Demo API 恢复后重启 Bot")
    elif quant.get('risk', '').startswith('🔴'):
        lines.append("├─ 总体风险：🔴 高")
        lines.append("├─ 原因：库存层数已打满")
        lines.append(f"└─ 建议动作：{quant.get('action', '立即暂停新开仓')}")
    elif quant.get('risk', '').startswith('🟡'):
        lines.append("├─ 总体风险：🟡 中等")
        lines.append("├─ 原因：库存接近上限")
        lines.append(f"└─ 建议动作：{quant.get('action', '关注加仓节奏')}")
    else:
        lines.append("├─ 总体风险：🟢 低")
        lines.append("├─ 原因：各模块运行正常")
        lines.append("└─ 建议动作：保持当前节奏，继续观察")
    
    lines.append("")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def main(user_input=""):
    # 检测模式
    mode = detect_mode(user_input)
    
    print("🔄 正在获取数据...")
    
    # 获取各模块数据
    quant = parse_quant()
    news = parse_news()
    macro = parse_macro()
    bot_status = check_bot_status()
    demo_status = check_demo_api()
    
    # 输出
    output = format_output(quant, news, macro, bot_status, demo_status)
    print(output)


if __name__ == "__main__":
    user_input = sys.argv[1] if len(sys.argv) > 1 else ""
    main(user_input)
