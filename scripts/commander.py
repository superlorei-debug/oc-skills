#!/usr/bin/env python3
"""
Commander - 主控汇总模块 V12
标准化 JSON 输出 + 文本展示
"""
import subprocess
import json
import os
import sys
from datetime import datetime

HISTORY_DIR = "data/history/commander"

# 常量定义
STATUS_EXECUTED = "executed"
STATUS_NO_UPDATE = "no_update"
STATUS_FAILED = "failed"
STATUS_NOT_CONNECTED = "not_connected"
STATUS_DEGRADED = "degraded"

VAL_NA = None  # 使用 null


def detect_mode(user_input):
    text = user_input.lower()
    detail_keywords = ["详细版", "详细看看", "展开", "完整", "具体"]
    return "detail" if any(k in text for k in detail_keywords) else "simple"


def run_cmd(path):
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
    try:
        r = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        for line in r.stdout.split("\n"):
            if "bot.py" in line and "grep" not in line:
                parts = line.split()
                return {"running": True, "pid": parts[1]}
        return {"running": False, "pid": None}
    except:
        return {"running": False, "pid": None}


def get_exec_mode():
    try:
        with open("/tmp/binance-spot-grid-bot/.env") as f:
            for line in f:
                if "EXECUTION_MODE=" in line:
                    return line.split("=")[1].strip()
    except:
        pass
    return None


def check_demo_api():
    """检查 Demo API 连接状态（调用实际接口验证）"""
    import requests
    import time
    import hmac
    import hashlib
    
    API_KEY = "cKMt8UxEo5Jse8r2oZQXMxwyeeRXO4VKgsaRGRuWZUI7Bqjmz9d4CmIiFTHY0ffo"
    API_SECRET = "kDFwRV1OY0Z7pvCitr42CfcwjOEXMFigu3rF9Nh3Du0ssoPrJGe0JmuTRuENPCpU"
    BASE_URL = "https://demo-api.binance.com"
    
    try:
        # 尝试调用实际接口（账户查询）
        ts = int(time.time() * 1000)
        query = f"timestamp={ts}&recvWindow=10000"
        signature = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
        url = f"{BASE_URL}/api/v3/account?{query}&signature={signature}"
        
        resp = requests.get(url, headers={"X-MBX-APIKEY": API_KEY}, timeout=5)
        
        if resp.status_code == 200:
            return {"connected": True, "latency_ms": int(resp.elapsed.total_seconds() * 1000)}
        else:
            return {"connected": False, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        error_msg = str(e)
        if "502" in error_msg:
            return {"connected": False, "error": "502 Bad Gateway"}
        return {"connected": False, "error": error_msg[:30]}


def parse_quant():
    """解析量化模块，返回标准化结构"""
    out, err, code = run_cmd("scripts/quant_report.py")
    
    result = {
        "module_execution_status": STATUS_FAILED,
        "target_mode": None,
        "actual_mode": None,
        "degrade_reason": None,
        "account_data_status": None,
        "market_data_status": None,
        "order_data_status": None,
        "data_validity": False,
        "last_success_sync": None,
        "data": {
            "price": None,
            "balance_usdt": None,
            "position_btc": None,
            "layers_used": None,
            "layers_limit": None,
            "utilization_pct": None,
            "orders_count": None,
            "status": None,
            "risk_reason": None,
            "action": None
        }
    }
    
    # 获取执行模式
    target_mode = get_exec_mode()
    result["target_mode"] = target_mode
    
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
            
            price_val = data.get("price_usd", 0)
            
            if price_val and price_val > 0:
                result["module_execution_status"] = STATUS_EXECUTED
                result["data_validity"] = True
                result["account_data_status"] = "success"
                result["market_data_status"] = "success"
                result["order_data_status"] = "success"
                result["last_success_sync"] = data.get("updated_at")
                
                result["data"] = {
                    "price": price_val,
                    "balance_usdt": data.get("total_u"),
                    "position_btc": data.get("position_btc"),
                    "layers_used": data.get("inventory_layers_used"),
                    "layers_limit": data.get("inventory_layers_limit"),
                    "utilization_pct": data.get("capital_utilization_pct"),
                    "orders_count": data.get("open_orders_count"),
                    "status": data.get("status"),
                    "risk_reason": data.get("risk_reason"),
                    "action": data.get("top_action")
                }
                
                if data.get("status") == "critical":
                    result["data"]["status"] = "critical"
                elif data.get("status") == "warning":
                    result["data"]["status"] = "warning"
                else:
                    result["data"]["status"] = "ok"
            else:
                if not demo_status["connected"]:
                    result["module_execution_status"] = STATUS_DEGRADED
                    result["actual_mode"] = "paper"
                    result["degrade_reason"] = "Demo API 502 Bad Gateway"
                    result["account_data_status"] = "failed"
                    result["market_data_status"] = "failed"
                    result["order_data_status"] = "failed"
    
    except Exception as e:
        result["degrade_reason"] = str(e)[:100]
    
    return result


def parse_news():
    out, err, code = run_cmd("scripts/news_report.py")
    
    result = {
        "module_execution_status": STATUS_NOT_CONNECTED,
        "fetch_mode": None,
        "article_count": None,
        "last_update": None
    }
    
    if code != 0 or err:
        result["module_execution_status"] = STATUS_FAILED
        return result
    
    if "实时模式" in out:
        result["module_execution_status"] = STATUS_EXECUTED
        result["fetch_mode"] = "realtime"
    elif "缓存模式" in out:
        result["module_execution_status"] = STATUS_EXECUTED
        result["fetch_mode"] = "cache"
    else:
        result["module_execution_status"] = STATUS_NO_UPDATE
    
    return result


def parse_macro():
    out, err, code = run_cmd("scripts/macro_report.py")
    
    result = {
        "module_execution_status": STATUS_NOT_CONNECTED,
        "phase": None,
        "strategy": None,
        "advice": None
    }
    
    if code != 0 or err:
        result["module_execution_status"] = STATUS_FAILED
        return result
    
    if "当前阶段" in out:
        result["module_execution_status"] = STATUS_EXECUTED
        for line in out.split("\n"):
            if "当前阶段：" in line and "定义" not in line:
                result["phase"] = line.split("：")[-1].strip()
            elif "家庭策略：" in line and "定义" not in line:
                result["strategy"] = line.split("：")[-1].strip()
            elif "一句话建议：" in line:
                result["advice"] = line.split("：")[-1].strip()
    
    return result


def generate_actions(quant, demo_status):
    """根据状态生成可执行动作"""
    actions = []
    
    if not demo_status["connected"]:
        actions.append({
            "id": 1,
            "priority": "high",
            "description": "暂不依据当前 Demo 数据做交易判断",
            "reason": "Demo API 异常，数据可能不准确"
        })
        actions.append({
            "id": 2,
            "priority": "high",
            "description": "检查 Demo API 恢复情况",
            "reason": "当前 API 返回 502"
        })
        actions.append({
            "id": 3,
            "priority": "medium",
            "description": "检查 Dashboard 是否正确显示降级状态",
            "reason": "确保监控正确"
        })
        actions.append({
            "id": 4,
            "priority": "medium",
            "description": "恢复后重新校验余额、价格、订单同步",
            "reason": "确保数据一致性"
        })
        actions.append({
            "id": 5,
            "priority": "high",
            "description": "等待 Demo API 恢复后重启 Bot",
            "reason": "降级模式下交易不真实执行"
        })
    elif quant.get("data", {}).get("status") == "critical":
        actions.append({
            "id": 1,
            "priority": "high",
            "description": quant.get("data", {}).get("action", "立即暂停新开仓"),
            "reason": "库存层数已打满"
        })
    elif quant.get("data", {}).get("status") == "warning":
        actions.append({
            "id": 1,
            "priority": "medium",
            "description": quant.get("data", {}).get("action", "关注加仓节奏"),
            "reason": "库存接近上限"
        })
    else:
        actions.append({
            "id": 1,
            "priority": "low",
            "description": "保持当前节奏，继续观察",
            "reason": "各模块运行正常"
        })
    
    return actions


def calculate_overall_status(quant, demo_status):
    """计算总体状态"""
    if not demo_status["connected"]:
        return "degraded"
    if quant.get("data", {}).get("status") == "critical":
        return "critical"
    if quant.get("data", {}).get("status") == "warning":
        return "warning"
    return "ok"


def build_report():
    """构建完整报告"""
    bot_status = check_bot_status()
    demo_status = check_demo_api()
    
    quant = parse_quant()
    news = parse_news()
    macro = parse_macro()
    
    overall_status = calculate_overall_status(quant, demo_status)
    actions = generate_actions(quant, demo_status)
    
    report = {
        "schema_version": "v1",
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "overall_status": overall_status,
        "quant": quant,
        "news": news,
        "macro": macro,
        "system": {
            "bot": bot_status,
            "demo_api": demo_status,
            "target_mode": quant.get("target_mode"),
            "actual_mode": quant.get("actual_mode") or quant.get("target_mode"),
            "degrade_reason": quant.get("degrade_reason")
        },
        "actions": actions
    }
    
    return report


def format_text_report(report):
    """将 JSON 转换为可读文本"""
    q = report["quant"]
    n = report["news"]
    m = report["macro"]
    s = report["system"]
    a = report["actions"]
    
    lines = []
    
    lines.append("=" * 60)
    lines.append("📋 今日总览")
    lines.append("=" * 60)
    lines.append(f"📅 报告时间：{report['generated_at']}")
    lines.append("")
    
    # 一、量化交易
    lines.append("一、量化交易")
    lines.append("-" * 40)
    lines.append(f"├─ 模块执行状态：{q['module_execution_status']}")
    
    if q['module_execution_status'] == STATUS_DEGRADED:
        lines.append(f"├─ 目标运行模式：{q['target_mode']}")
        lines.append(f"├─ 当前实际模式：{q['actual_mode']} (降级)")
        lines.append(f"├─ 降级原因：{q['degrade_reason']}")
    else:
        lines.append(f"├─ 当前运行模式：{q['target_mode']}")
    
    lines.append(f"├─ 数据有效性：{'✅ 有效' if q['data_validity'] else '❌ 无效'}")
    
    if q['data_validity']:
        d = q['data']
        lines.append(f"├─ BTC 价格：${d['price']:,.2f}" if d['price'] else f"├─ BTC 价格：N/A")
        lines.append(f"├─ USDT 余额：{d['balance_usdt']}")
        lines.append(f"├─ BTC 持仓：{d['position_btc']}")
        lines.append(f"├─ 库存层数：{d['layers_used']}/{d['layers_limit']}")
        lines.append(f"├─ 资金利用率：{d['utilization_pct']}%" if d['utilization_pct'] else f"├─ 资金利用率：N/A")
        lines.append(f"├─ 挂单数量：{d['orders_count']}单" if d['orders_count'] else f"├─ 挂单数量：N/A")
        lines.append(f"├─ 当前状态：{d['status']}")
        lines.append(f"└─ 建议动作：{d['action']}")
    else:
        lines.append(f"├─ BTC 价格：N/A")
        lines.append(f"├─ USDT 余额：N/A")
        lines.append(f"├─ BTC 持仓：N/A")
        lines.append(f"└─ 建议动作：检查 Demo API 连接")
    
    lines.append("")
    
    # 二、新闻
    lines.append("二、新闻与地缘")
    lines.append("-" * 40)
    if n['module_execution_status'] == STATUS_EXECUTED:
        lines.append(f"├─ 模块执行状态：已执行")
        lines.append(f"├─ 获取模式：{n['fetch_mode']}")
        lines.append(f"└─ 新闻数量：{n['article_count']}条" if n['article_count'] else f"└─ 新闻数量：0条")
    elif n['module_execution_status'] == STATUS_NO_UPDATE:
        lines.append(f"└─ 📝 暂无新闻更新")
    else:
        lines.append(f"└─ ❌ 执行失败")
    
    lines.append("")
    
    # 三、宏观
    lines.append("三、宏观环境")
    lines.append("-" * 40)
    if m['module_execution_status'] == STATUS_EXECUTED:
        lines.append(f"├─ 模块执行状态：已执行")
        lines.append(f"├─ 当前阶段：{m['phase']}")
        lines.append(f"├─ 家庭策略：{m['strategy']}")
        lines.append(f"└─ 一句话建议：{m['advice']}")
    elif m['module_execution_status'] == STATUS_NO_UPDATE:
        lines.append(f"└─ 📝 暂无宏观更新")
    else:
        lines.append(f"└─ ❌ 执行失败")
    
    lines.append("")
    
    # 四、系统状态
    lines.append("四、系统状态")
    lines.append("-" * 40)
    if s['bot']['running']:
        lines.append(f"├─ Bot 运行：✅ 运行中 (PID: {s['bot']['pid']})")
    else:
        lines.append(f"├─ Bot 运行：❌ 未运行")
    
    if s['demo_api']['connected']:
        lines.append(f"├─ Demo API：✅ 正常")
    else:
        lines.append(f"├─ Demo API：❌ 异常")
    
    if s['degrade_reason']:
        lines.append(f"├─ 目标执行模式：{s['target_mode']}")
        lines.append(f"├─ 当前执行模式：{s['actual_mode']} (降级)")
        lines.append(f"└─ ⚠️ 系统状态：降级运行")
    else:
        lines.append(f"└─ 执行模式：{s['target_mode']}")
    
    lines.append("")
    
    # 五、今日建议
    lines.append("五、今日建议")
    lines.append("-" * 40)
    
    status_emoji = {"degraded": "⚠️", "critical": "🔴", "warning": "🟡", "ok": "🟢"}
    lines.append(f"├─ 总体风险：{status_emoji.get(report['overall_status'], '⚠️')} {report['overall_status'].upper()}")
    
    for action in a:
        lines.append(f"├─ [{action['priority']}] {action['description']}")
    
    lines.append("")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def main(user_input=""):
    mode = detect_mode(user_input)
    
    # 构建报告
    report = build_report()
    
    # 保存 JSON
    output_file = "/Users/mac/.openclaw/workspace/openclaw-project/data/latest/commander_status.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # 文本输出
    print(format_text_report(report))


if __name__ == "__main__":
    user_input = sys.argv[1] if len(sys.argv) > 1 else ""
    main(user_input)
