#!/usr/bin/env python3
"""
Macro Advisor - 宏观/家庭理财模块 V2
结论 + 定义 + 依据 + 影响
"""
import json
import os
from datetime import datetime

PROFILE_FILE = "data/cache/macro_profile.json"

DEFAULT_PROFILE = {
    "income": 30000,
    "fixed_cost": 12000,
    "savings": 250000,
    "risk_tolerance": "稳健",
    "goals": ["保留流动性", "稳健存钱"]
}

def load_profile():
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE) as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_PROFILE

# ===== 宏观阶段定义 =====
PHASE_DEFINITIONS = {
    "偏弱": {
        "definition": "经济下行压力较大，增长动力不足，消费、就业、收入预期都比较疲软，整体环境需要更保守。",
        "reasons": [
            "经济增长动力不足",
            "消费需求疲软",
            "就业压力较大",
            "居民收入预期谨慎"
        ]
    },
    "弱修复": {
        "definition": "经济在恢复，但恢复力度还不强，消费、就业、收入预期仍有分化，整体环境暂时不适合太激进。",
        "reasons": [
            "消费恢复不均衡",
            "就业预期仍偏谨慎",
            "居民风险偏好还不高",
            "政策支持逐步显现"
        ]
    },
    "结构分化": {
        "definition": "不同行业、区域表现差异很大，有的地方增长快，有的地方还在调整，机会和风险并存。",
        "reasons": [
            "行业分化明显",
            "区域发展不均衡",
            "新旧动能转换中",
            "结构性机会出现"
        ]
    },
    "温和回暖": {
        "definition": "经济呈现稳健增长态势，消费、就业、预期都偏向积极，可以适度增加风险资产配置。",
        "reasons": [
            "消费信心回升",
            "就业形势改善",
            "居民收入增长",
            "政策环境友好"
        ]
    }
}

# ===== 家庭策略定义 =====
STRATEGY_DEFINITIONS = {
    "保守": {
        "definition": "家庭资金应以高流动性资产为主（现金、银行存款），风险资产比例控制在很低水平。",
        "implications": [
            "保留充足流动性",
            "避免高风险投资",
            "优先保障应急金",
            "等待更好时机"
        ]
    },
    "稳健偏保守": {
        "definition": "家庭资金仍应以现金、定存、稳健类资产为主，风险资产比例不要太高。",
        "implications": [
            "先保留流动性",
            "不要激进加大高风险配置",
            "可以适度增加稳健配置",
            "控制整体风险敞口"
        ]
    },
    "平衡": {
        "definition": "现金、稳健资产、风险资产保持相对均衡的配置，可以适度参与市场机会。",
        "implications": [
            "保持常规配置比例",
            "可以适度参与",
            "注意仓位控制",
            "关注风险变化"
        ]
    },
    "积极": {
        "definition": "可以增加风险资产配置比例，把握市场机会，但也要做好波动承受准备。",
        "implications": [
            "增加权益类配置",
            "把握结构性机会",
            "做好波动承受准备",
            "注意及时止盈"
        ]
    }
}

# ===== 阶段到策略的映射 =====
PHASE_TO_STRATEGY = {
    "偏弱": "保守",
    "弱修复": "稳健偏保守",
    "结构分化": "平衡",
    "温和回暖": "积极"
}

def analyze_macro():
    """宏观分析 - V2 用简化判断"""
    return {
        "phase": "弱修复",
        "confidence": "中等"
    }

def get_advice(phase, strategy):
    """获取建议"""
    if strategy == "保守":
        return "当前环境下以安全为主，减少风险资产，优先保障流动性。"
    elif strategy == "稳健偏保守":
        return "当前先求稳，保留安全垫，再逐步优化配置。"
    elif strategy == "平衡":
        return "保持均衡配置，适度参与市场机会，注意风险控制。"
    else:
        return "可以适度增加风险资产，把握市场机会，但需做好波动准备。"

def output():
    profile = load_profile()
    macro = analyze_macro()
    
    phase = macro.get("phase", "弱修复")
    strategy = PHASE_TO_STRATEGY.get(phase, "稳健偏保守")
    
    phase_info = PHASE_DEFINITIONS.get(phase, PHASE_DEFINITIONS["弱修复"])
    strategy_info = STRATEGY_DEFINITIONS.get(strategy, STRATEGY_DEFINITIONS["稳健偏保守"])
    
    advice = get_advice(phase, strategy)
    
    print("="*50)
    print("📊 宏观 / 家庭理财简报")
    print("="*50)
    print()
    print(f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    
    print("三、宏观 / 家庭理财")
    print()
    print(f"1. 当前阶段：{phase}")
    print()
    print(f"2. 当前阶段定义：{phase_info['definition']}")
    print()
    print(f"3. 为什么是这个阶段：")
    for reason in phase_info["reasons"]:
        print(f"  - {reason}")
    print()
    print(f"4. 家庭策略：{strategy}")
    print()
    print(f"5. 家庭策略定义：{strategy_info['definition']}")
    print()
    print(f"6. 对我现在意味着什么：")
    for impl in strategy_info["implications"]:
        print(f"  - {impl}")
    print()
    print(f"7. 一句话建议：{advice}")
    print()
    print("="*50)

def main():
    output()

if __name__ == "__main__":
    main()
