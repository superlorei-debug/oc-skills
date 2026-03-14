#!/usr/bin/env python3
"""
Upgrade Gate - 升级闸门
V1 先搭框架，默认不自动执行

输出: data/evolution/upgrade_decision.json
"""
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv('/Users/mac/.openclaw/workspace/openclaw-project/runs/grid_bot/.env')

DATA_DIR = "/Users/mac/.openclaw/workspace/openclaw-project/data"
LATEST_DIR = f"{DATA_DIR}/latest"
EVOLUTION_DIR = f"{DATA_DIR}/evolution"

# 升级条件
UPGRADE_CONDITIONS = {
    "min_score": 70,  # 最低评分
    "min_stability_days": 3,  # 最低稳定天数
    "require_manual_approval": True,  # 需要人工批准
}

# 禁止升级条件
BLOCK_CONDITIONS = [
    "data_invalid",
    "demo_api_down",
    "mode_degraded",
    "risk_high",
]

def load_data():
    """加载数据"""
    data = {}
    
    for fname in ['commander_status.json', 'quant_report.json']:
        try:
            with open(f"{LATEST_DIR}/{fname}") as f:
                data[fname.replace('.json', '')] = json.load(f)
        except:
            pass
    
    # 加载评估数据
    for fname in ['strategy_score.json', 'market_regime.json', 'parameter_candidates.json']:
        try:
            with open(f"{EVOLUTION_DIR}/{fname}") as f:
                data[fname.replace('.json', '')] = json.load(f)
        except:
            pass
    
    return data

def check_block_conditions(data):
    """检查禁止升级条件"""
    blocks = []
    
    commander = data.get("commander_status", {})
    quant = data.get("quant_report", {})
    
    # 检查数据有效性
    q_data = commander.get("quant", {})
    if not q_data.get("data_validity"):
        blocks.append("data_invalid")
    
    # 检查 Demo API
    system = commander.get("system", {})
    if not system.get("demo_api", {}).get("connected"):
        blocks.append("demo_api_down")
    
    # 检查模式
    runtime = commander.get("runtime", {})
    if runtime.get("actual_mode") != runtime.get("target_mode"):
        blocks.append("mode_degraded")
    
    # 检查策略评分
    score = data.get("strategy_score", {})
    scores = score.get("scores", {})
    if scores.get("overall", 0) < UPGRADE_CONDITIONS["min_score"]:
        blocks.append("low_score")
    
    return blocks

def evaluate_upgrade():
    """评估升级"""
    data = load_data()
    
    # 检查禁止条件
    blocks = check_block_conditions(data)
    
    if blocks:
        result = {
            "timestamp": datetime.now().isoformat(),
            "upgrade_available": False,
            "blocks": blocks,
            "decision": "BLOCKED",
            "reason": f"存在禁止升级条件: {', '.join(blocks)}",
            "auto_apply": False,
            "require_approval": True,
            "next_review_time": (datetime.now() + timedelta(hours=6)).isoformat(),
        }
    else:
        # 可以评估升级
        score = data.get("strategy_score", {})
        scores = score.get("scores", {})
        regime = data.get("market_regime", {}).get("regime", "稳定")
        candidates = data.get("parameter_candidates", {})
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "upgrade_available": True,
            "blocks": [],
            "decision": "PENDING_APPROVAL",
            "current_score": scores.get("overall", 0),
            "market_regime": regime,
            "recommended_candidate": candidates.get("recommended"),
            "auto_apply": False,  # V1 默认不自动
            "require_approval": True,  # V1 需要人工批准
            "approval_required_for": ["参数修改", "策略调整"],
            "next_review_time": (datetime.now() + timedelta(hours=24)).isoformat(),
        }
    
    return result

def save_result(result):
    """保存结果"""
    os.makedirs(EVOLUTION_DIR, exist_ok=True)
    
    with open(f"{EVOLUTION_DIR}/upgrade_decision.json", 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    from datetime import timedelta
    
    result = evaluate_upgrade()
    save_result(result)
    
    print("=" * 50)
    print(f"🚪 升级闸门")
    print("=" * 50)
    print(f"可升级: {'是' if result['upgrade_available'] else '否'}")
    print(f"决策: {result['decision']}")
    
    if result["blocks"]:
        print("-" * 50)
        print("禁止原因:")
        for b in result["blocks"]:
            print(f"  ❌ {b}")
    else:
        print("-" * 50)
        print(f"当前评分: {result.get('current_score', '-')}")
        print(f"市场状态: {result.get('market_regime', '-')}")
        print(f"推荐方案: {result.get('recommended_candidate', '-')}")
    
    print("-" * 50)
    print(f"自动应用: {'是' if result['auto_apply'] else '否'}")
    print(f"需要审批: {'是' if result['require_approval'] else '否'}")
    print("=" * 50)
    print(f"\n✅ 已保存到: {EVOLUTION_DIR}/upgrade_decision.json")
