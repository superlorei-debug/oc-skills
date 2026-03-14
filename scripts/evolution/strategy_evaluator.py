#!/usr/bin/env python3
"""
Strategy Evaluator - 策略评估器
对当前策略进行打分和复盘

输出: data/evolution/strategy_score.json
"""
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv('/Users/mac/.openclaw/workspace/openclaw-project/runs/grid_bot/.env')

DATA_DIR = "/Users/mac/.openclaw/workspace/openclaw-project/data"
LATEST_DIR = f"{DATA_DIR}/latest"
EVOLUTION_DIR = f"{DATA_DIR}/evolution"

def load_data():
    """加载数据"""
    data = {}
    
    for fname in ['commander_status.json', 'quant_report.json', 'news_report.json', 'macro_report.json']:
        try:
            with open(f"{LATEST_DIR}/{fname}") as f:
                key = fname.replace('.json', '').replace('_status', '')
                data[key] = json.load(f)
        except:
            pass
    
    return data

def evaluate_strategy():
    """评估策略"""
    data = load_data()
    
    scores = {
        "stability": 0,
        "performance": 0,
        "risk_control": 0,
        "overall": 0,
    }
    
    factors = []
    
    # 1. 稳定性评估
    quant = data.get("quant_report", {})
    commander = data.get("commander_status", {})
    
    # 检查数据有效性
    if quant.get("status") == "ok":
        scores["stability"] += 40
        factors.append("✅ 策略状态正常")
    else:
        scores["stability"] += 0
        factors.append("❌ 策略状态异常")
    
    # 检查交易权限
    q_data = commander.get("quant", {})
    if q_data.get("data_validity"):
        scores["stability"] += 30
        factors.append("✅ 数据有效")
    else:
        scores["stability"] += 0
        factors.append("⚠️ 数据无效")
    
    # 检查 Demo API
    system = commander.get("system", {})
    if system.get("demo_api", {}).get("connected"):
        scores["stability"] += 30
        factors.append("✅ Demo API 正常")
    else:
        scores["stability"] += 0
        factors.append("❌ Demo API 异常")
    
    # 2. 表现评估
    util = quant.get("capital_utilization_pct", 0)
    if util > 0:
        scores["performance"] += 50
        factors.append(f"✅ 资金利用中 ({util}%)")
    else:
        scores["performance"] += 20
        factors.append("⚠️ 资金未利用")
    
    # 挂单情况
    orders = quant.get("open_orders_count", 0)
    if orders > 0:
        scores["performance"] += 30
        factors.append(f"✅ 有挂单 ({orders}单)")
    else:
        scores["performance"] += 10
        factors.append("⚠️ 无挂单")
    
    # 库存层数
    layers = quant.get("inventory_layers_used", 0)
    if layers > 0:
        scores["performance"] += 20
        factors.append(f"✅ 库存层数: {layers}")
    else:
        scores["performance"] += 0
        factors.append("⚠️ 库存为空")
    
    # 3. 风控评估
    runtime = commander.get("runtime", {})
    if runtime.get("actual_mode") == runtime.get("target_mode"):
        scores["risk_control"] += 40
        factors.append("✅ 模式正常")
    else:
        scores["risk_control"] += 20
        factors.append("⚠️ 模式降级")
    
    if q_data.get("data_validity"):
        scores["risk_control"] += 40
        factors.append("✅ 数据有效")
    else:
        scores["risk_control"] += 0
        factors.append("❌ 数据失效")
    
    # 持仓检查
    position = quant.get("position_btc", 0)
    if position > 0:
        scores["risk_control"] += 20
        factors.append(f"✅ 有持仓")
    else:
        scores["risk_control"] += 20
        factors.append("📊 空仓中")
    
    # 4. 综合评分
    scores["overall"] = int((scores["stability"] + scores["performance"] + scores["risk_control"]) / 3)
    
    # 生成评估结果
    result = {
        "timestamp": datetime.now().isoformat(),
        "scores": scores,
        "factors": factors,
        "summary": generate_summary(scores, factors),
        "current_params": {
            "symbol": quant.get("symbol"),
            "inventory_layers_limit": quant.get("inventory_layers_limit"),
            "utilization_target": "待定义",
        },
    }
    
    return result

def generate_summary(scores, factors):
    """生成摘要"""
    overall = scores["overall"]
    
    if overall >= 80:
        status = "优秀"
        advice = "策略运行良好，保持当前节奏"
    elif overall >= 60:
        status = "良好"
        advice = "策略运行正常，关注异常指标"
    elif overall >= 40:
        status = "一般"
        advice = "需要关注，建议检查系统状态"
    else:
        status = "警告"
        advice = "建议立即检查系统和参数"
    
    return {
        "status": status,
        "score": overall,
        "advice": advice,
    }

def save_result(result):
    """保存结果"""
    os.makedirs(EVOLUTION_DIR, exist_ok=True)
    
    with open(f"{EVOLUTION_DIR}/strategy_score.json", 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    result = evaluate_strategy()
    save_result(result)
    
    print("=" * 50)
    print(f"📊 策略评估报告")
    print("=" * 50)
    print(f"综合评分: {result['scores']['overall']}/100 ({result['summary']['status']})")
    print(f"稳定性: {result['scores']['stability']}/100")
    print(f"表现: {result['scores']['performance']}/100")
    print(f"风控: {result['scores']['risk_control']}/100")
    print("-" * 50)
    print("评估因素:")
    for f in result['factors']:
        print(f"  {f}")
    print("-" * 50)
    print(f"建议: {result['summary']['advice']}")
    print("=" * 50)
    print(f"\n✅ 已保存到: {EVOLUTION_DIR}/strategy_score.json")
