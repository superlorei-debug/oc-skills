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
    """检测用户意图模式"""
    text = user_input.lower()
    
    # 巡检/健康检查关键词
    health_keywords = ["系统状态", "巡检", "健康检查", "运行状态", "bot状态", "health", "检查"]
    # 今日关注详细版关键词
    detail_keywords = ["今天需要注意什么", "今日关注", "详细版", "今日风险", "今天要注意什么", "今日详细", "综合", "今日摘要"]
    
    if any(k in text for k in detail_keywords):
        return "daily_detail"
    elif any(k in text for k in health_keywords):
        return "health_check"
    else:
        return "simple"


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
    import subprocess
    
    bot_status = check_bot_status()
    demo_status = check_demo_api()
    
    quant = parse_quant()
    news = parse_news()
    macro = parse_macro()
    
    overall_status = calculate_overall_status(quant, demo_status)
    actions = generate_actions(quant, demo_status)
    
    # 获取 Git 版本信息
    try:
        git_rev = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd="/Users/mac/.openclaw/workspace/openclaw-project",
            capture_output=True, text=True, timeout=5
        )
        current_commit = git_rev.stdout.strip() if git_rev.returncode == 0 else "unknown"
    except:
        current_commit = "unknown"
    
    # 获取运行路径
    import os
    runtime_path = os.path.realpath("/Users/mac/.openclaw/workspace/openclaw-project/runs/grid_bot/bot.py")
    
    # 启动时间（从进程获取）
    start_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    report = {
        "schema_version": "v1",
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "overall_status": overall_status,
        "runtime": {
            "current_commit": current_commit,
            "runtime_path": runtime_path,
            "start_time": start_time,
            "restart_time": start_time,
            "target_mode": quant.get("target_mode"),
            "actual_mode": quant.get("actual_mode") or quant.get("target_mode"),
            "degrade_reason": quant.get("degrade_reason")
        },
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



def check_data_freshness():
    """检查数据新鲜度 - 基于真实同步时间"""
    import os
    from datetime import datetime
    
    # 从 commander_status.json 读取真实同步时间和有效性
    status_file = "/Users/mac/.openclaw/workspace/openclaw-project/data/latest/commander_status.json"
    
    freshness = "invalid"
    last_sync_time = None
    age_minutes = None
    data_validity = False
    
    if os.path.exists(status_file):
        try:
            with open(status_file) as f:
                data = json.load(f)
            
            # 获取数据有效性
            data_validity = data.get("quant", {}).get("data_validity", False)
            
            # 获取最后成功同步时间
            last_sync_time = data.get("quant", {}).get("last_success_sync")
            
            # 如果有同步时间，计算 freshness
            if last_sync_time:
                try:
                    dt = datetime.strptime(last_sync_time, "%Y-%m-%d %H:%M")
                    age_minutes = int((datetime.now() - dt).total_seconds() / 60)
                    
                    # 只有数据有效时才算 fresh
                    if not data_validity:
                        freshness = "invalid"
                    elif age_minutes < 30:
                        freshness = "fresh"
                    elif age_minutes < 120:
                        freshness = "stale"
                    else:
                        freshness = "expired"
                except:
                    freshness = "invalid"
            else:
                # 没有同步时间
                freshness = "invalid"
        except:
            freshness = "invalid"
    else:
        freshness = "invalid"
    
    return {
        "freshness": freshness,
        "last_sync_time": last_sync_time,
        "age_minutes": age_minutes,
        "data_validity": data_validity
    }


def format_daily_detail_report(report):
    """今日关注详细版"""
    q = report.get("quant", {})
    n = report.get("news", {})
    m = report.get("macro", {})
    s = report.get("system", {})
    r = report.get("runtime", {})
    
    freshness = check_data_freshness()
    
    lines = []
    lines.append("=" * 60)
    lines.append("📋 今日关注详细版")
    lines.append("=" * 60)
    lines.append(f"📅 报告时间：{report.get('generated_at', '')}")
    lines.append("")
    
    # 一、今日重点摘要
    lines.append("一、今日重点摘要")
    lines.append("-" * 40)
    
    overall = "警告"
    if freshness["freshness"] == "fresh" and s.get("demo_api", {}).get("connected"):
        overall = "正常"
    elif s.get("demo_api", {}).get("connected") == False:
        overall = "降级"
    elif freshness["freshness"] == "expired":
        overall = "警告"
    
    emoji = {"正常": "✅", "警告": "⚠️", "降级": "🔴"}
    lines.append(f"├─ 总体状态：{emoji.get(overall, '❓')} {overall}")
    
    if not s.get("demo_api", {}).get("connected"):
        lines.append(f"├─ 首要问题：Demo API 异常，系统降级运行")
    elif freshness["freshness"] == "expired":
        lines.append(f"├─ 首要问题：量化数据过期约 {freshness.get('age_minutes', 0)} 分钟，未自动刷新")
    elif q.get("data_validity") == False:
        lines.append(f"├─ 首要问题：量化数据无效")
    else:
        lines.append(f"├─ 首要问题：无")
    
    lines.append("")
    
    # 二、量化交易
    lines.append("二、量化交易")
    lines.append("-" * 40)
    
    freshness_emoji = {"fresh": "✅", "stale": "⚠️", "expired": "🔴", "invalid": "❌"}
    lines.append(f"├─ 数据新鲜度：{freshness_emoji.get(freshness.get('freshness', 'unknown'), '❓')} {freshness.get('freshness', 'unknown')}")
    lines.append(f"├─ 数据有效性：{'有效' if freshness.get('data_validity') else '无效'}")
    lines.append(f"├─ 最后成功同步：{freshness.get('last_sync_time', 'N/A')}")
    if freshness.get('age_minutes') is not None:
        lines.append(f"├─ 距最后同步：{freshness.get('age_minutes')} 分钟")
    else:
        lines.append(f"├─ 距最后同步：N/A")
    
    if q.get("data_validity"):
        d = q.get("data", {})
        lines.append(f"├─ BTC 价格：${d.get('price', 'N/A'):,.2f}" if d.get("price") else f"├─ BTC 价格：N/A")
        lines.append(f"├─ USDT 余额：{d.get('balance_usdt', 'N/A')}")
        lines.append(f"├─ BTC 持仓：{d.get('position_btc', 'N/A')}")
        lines.append(f"├─ 库存层数：{d.get('layers_used', 'N/A')}/{d.get('layers_limit', 'N/A')}")
        lines.append(f"├─ 资金利用率：{d.get('utilization_pct', 'N/A')}%")
        lines.append(f"└─ 当前状态：{d.get('status', 'N/A')}")
    else:
        lines.append(f"├─ BTC 价格：获取失败")
        lines.append(f"├─ USDT 余额：获取失败")
        lines.append(f"├─ BTC 持仓：获取失败")
        lines.append(f"└─ ⚠️ 原因：量化数据过期或不可用")
    
    lines.append("")
    
    # 三、新闻与地缘
    lines.append("三、新闻与地缘")
    lines.append("-" * 40)
    if n.get("module_execution_status") == STATUS_EXECUTED:
        lines.append(f"├─ 状态：已执行")
        lines.append(f"├─ 模式：{n.get('fetch_mode', 'N/A')}")
        lines.append(f"└─ 新闻数量：{n.get('article_count', 0)} 条")
    else:
        lines.append(f"└─ 📝 暂无关键更新")
    
    lines.append("")
    
    # 四、宏观环境
    lines.append("四、宏观环境")
    lines.append("-" * 40)
    if m.get("module_execution_status") == STATUS_EXECUTED:
        lines.append(f"├─ 状态：已执行")
        lines.append(f"├─ 当前阶段：{m.get('phase', 'N/A')}")
        lines.append(f"├─ 家庭策略：{m.get('strategy', 'N/A')}")
        lines.append(f"└─ 一句话建议：{m.get('advice', 'N/A')}")
    else:
        lines.append(f"└─ 📝 暂无关键更新")
    
    lines.append("")
    
    # 五、系统运行
    lines.append("五、系统运行")
    lines.append("-" * 40)
    lines.append(f"├─ Bot 进程：{'✅ 运行中' if s.get('bot', {}).get('running') else '❌ 未运行'}")
    lines.append(f"├─ 目标模式：{r.get('target_mode', 'N/A')}")
    lines.append(f"├─ 实际模式：{r.get('actual_mode', 'N/A')}")
    lines.append(f"├─ Demo API：{'✅ 正常' if s.get('demo_api', {}).get('connected') else '❌ 异常'}")
    
    if r.get("degrade_reason"):
        lines.append(f"├─ 降级原因：{r.get('degrade_reason')}")
        lines.append(f"└─ ⚠️ 系统已降级，不要依据 Demo 数据做交易判断")
    else:
        lines.append(f"└─ 降级原因：无")
    
    lines.append("")
    
    # 六、今日动作建议
    lines.append("六、今日动作建议")
    lines.append("-" * 40)
    
    suggestions = []
    
    if not s.get("demo_api", {}).get("connected"):
        suggestions.append("1. Demo API 异常，暂不依据 Demo 数据做交易判断")
        suggestions.append("2. 等待 API 恢复后重启 Bot 触发同步")
    elif freshness["freshness"] == "expired":
        suggestions.append("1. ⚠️ 量化数据过期约 3 小时，需立即刷新")
        suggestions.append("2. 建议重启 Bot 触发 quant_report.json 重新生成")
        suggestions.append("3. 检查数据刷新钩子是否执行")
    elif q.get("data_validity") == False:
        suggestions.append("1. 量化数据无效，需检查生成链")
        suggestions.append("2. 手动执行 python3 scripts/quant_report.py")
    else:
        suggestions.append("1. 系统运行正常，保持当前节奏")
        suggestions.append("2. 继续观察 Demo API 状态")
    
    for suggestion in suggestions:
        lines.append(f"├─ {suggestion}")
    
    lines.append("")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def format_health_check_report(report):
    """巡检报告"""
    lines = []
    lines.append("【AI Quant Brain｜健康巡检】")
    lines.append(f"时间：{report.get('generated_at', '')}")
    lines.append("")
    
    r = report.get("runtime", {})
    s = report.get("system", {})
    q = report.get("quant", {})
    
    lines.append("【1. 运行路径】")
    lines.append(f"  runtime_path: {r.get('runtime_path', 'N/A')}")
    lines.append(f"  代码源: {'✅ 单源' if 'scripts' in str(r.get('runtime_path', '')) else '❌ 异常'}")
    lines.append("")
    
    lines.append("【2. 版本信息】")
    lines.append(f"  current_commit: {r.get('current_commit', 'N/A')}")
    lines.append(f"  start_time: {r.get('start_time', 'N/A')}")
    lines.append(f"  target_mode: {r.get('target_mode', 'N/A')}")
    lines.append(f"  actual_mode: {r.get('actual_mode', 'N/A')}")
    lines.append("")
    
    can_trade = q.get("data_validity", False)
    lines.append("【3. 交易安全状态】")
    lines.append(f"  can_trade: {'✅ 可交易' if can_trade else '❌ 禁止交易'}")
    if r.get("degrade_reason"):
        lines.append(f"  降级原因: {r.get('degrade_reason')}")
    lines.append("")
    
    lines.append("【4. Bot 进程】")
    lines.append(f"  运行状态: {'✅ 运行中' if s.get('bot', {}).get('running') else '❌ 未运行'}")
    lines.append("")
    
    lines.append("=" * 60)
    
    return "\n".join(lines)

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
    
    # 根据模式输出不同内容
    if mode == "daily_detail":
        print(format_daily_detail_report(report))
    elif mode == "health_check":
        print(format_health_check_report(report))
    else:
        print(format_text_report(report))


if __name__ == "__main__":
    user_input = sys.argv[1] if len(sys.argv) > 1 else ""
    main(user_input)


