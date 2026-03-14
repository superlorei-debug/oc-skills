#!/usr/bin/env python3
"""
Parameter Lab - 参数实验室
输出候选参数建议，但不自动生效

输出: data/evolution/parameter_candidates.json
"""
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/Users/mac/.openclaw/workspace/openclaw-project/runs/grid_bot/.env')

DATA_DIR = "/Users/mac/.openclaw/workspace/openclaw-project/data"
LATEST_DIR = f"{DATA_DIR}/latest"
EVOLUTION_DIR = f"{DATA_DIR}/evolution"

def load_data():
    """加载数据"""
    data = {}
    
    for fname in ['quant_report.json', 'market_regime.json']:
        try:
            with open(f"{LATEST_DIR}/{fname}") as f:
                data[fname.replace('.json', '')] = json.load(f)
        except:
            pass
    
    # 尝试加载 evolution 数据
    try:
        with open(f"{EVOLUTION_DIR}/market_regime.json") as f:
            data['market_regime'] = json.load(f)
    except:
        pass
    
    return data

def generate_candidates():
    """生成参数建议"""
    data = load_data()
    
    # 获取当前参数
    quant = data.get("quant_report", {})
    current = {
        "inventory_layers_limit": quant.get("inventory_layers_limit", 6),
        "symbol": quant.get("symbol", "BTCUSDT"),
        "status": quant.get("status"),
    }
    
    # 获取市场状态
    regime_data = data.get("market_regime", {})
    regime = regime_data.get("regime", "稳定")
    
    # 基于市场状态生成候选
    candidates = []
    
    # 候选 A: 保守方案
    candidate_a = {
        "name": "保守方案",
        "description": "降低风险，减少资金占用",
        "params": {
            "inventory_layers_limit": 4,
            "grid_spacing_pct": 2.0,
            "max_position_pct": 10,
        },
        "suitable_regimes": ["下行", "高波动", "风险事件"],
        "priority": 1 if regime in ["下行", "高波动", "风险事件"] else 3,
    }
    candidates.append(candidate_a)
    
    # 候选 B: 均衡方案
    candidate_b = {
        "name": "均衡方案",
        "description": "保持当前节奏，风险收益平衡",
        "params": {
            "inventory_layers_limit": 6,
            "grid_spacing_pct": 1.5,
            "max_position_pct": 15,
        },
        "suitable_regimes": ["震荡", "稳定"],
        "priority": 2 if regime in ["震荡", "稳定"] else 2,
    }
    candidates.append(candidate_b)
    
    # 候选 C: 激进方案
    candidate_c = {
        "name": "激进方案",
        "description": "增加仓位，追求更高收益",
        "params": {
            "inventory_layers_limit": 8,
            "grid_spacing_pct": 1.0,
            "max_position_pct": 20,
        },
        "suitable_regimes": ["上行", "稳定"],
        "priority": 3 if regime in ["上行", "稳定"] else 1,
    }
    candidates.append(candidate_c)
    
    # 根据当前市场状态推荐
    recommended = None
    for c in candidates:
        if regime in c["suitable_regimes"] and c["priority"] == 1:
            recommended = c["name"]
            break
    
    if not recommended:
        recommended = "均衡方案"
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "current_params": current,
        "market_regime": regime,
        "candidates": candidates,
        "recommended": recommended,
        "auto_apply": False,  # V1 默认不自动应用
        "require_approval": True,  # V1 需要人工批准
    }
    
    return result

def save_result(result):
    """保存结果"""
    os.makedirs(EVOLUTION_DIR, exist_ok=True)
    
    with open(f"{EVOLUTION_DIR}/parameter_candidates.json", 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    result = generate_candidates()
    save_result(result)
    
    print("=" * 50)
    print(f"🔬 参数实验室")
    print("=" * 50)
    print(f"当前市场状态: {result['market_regime']}")
    print(f"推荐方案: {result['recommended']}")
    print("-" * 50)
    print("候选方案:")
    for c in result['candidates']:
        print(f"\n【{c['name']}】{c['description']}")
        print(f"  网格层数: {c['params']['inventory_layers_limit']}")
        print(f"  网格间距: {c['params']['grid_spacing_pct']}%")
        print(f"  最大仓位: {c['params']['max_position_pct']}%")
        print(f"  适合状态: {', '.join(c['suitable_regimes'])}")
    print("-" * 50)
    print(f"自动应用: {'是' if result['auto_apply'] else '否'}")
    print(f"需要审批: {'是' if result['require_approval'] else '否'}")
    print("=" * 50)
    print(f"\n✅ 已保存到: {EVOLUTION_DIR}/parameter_candidates.json")
