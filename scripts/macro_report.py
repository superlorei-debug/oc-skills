#!/usr/bin/env python3
"""
Macro Advisor - 宏观/家庭理财模块 V1
"""
import json
import os
from datetime import datetime

PROFILE_FILE = "/tmp/macro_profile.json"

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

def analyze_macro():
    return {
        "phase": "弱修复",
        "conclusion": "经济仍在恢复中，消费和就业有分化",
        "basis": "消费分化，就业结构性矛盾"
    }

def family_advice(profile, macro):
    phase = macro.get("phase", "弱修复")
    
    if phase == "偏弱":
        cash_ratio = "30-35%"
        fixed_ratio = "40-45%"
        risk_ratio = "10-15%"
        emergency = "预留12个月生活费"
        advice = "以安全为主，减少风险资产"
    elif phase == "弱修复":
        cash_ratio = "25-30%"
        fixed_ratio = "35-40%"
        risk_ratio = "15-20%"
        emergency = "预留9-12个月生活费"
        advice = "可以适度增加稳健配置"
    elif phase == "结构分化":
        cash_ratio = "20-25%"
        fixed_ratio = "35-40%"
        risk_ratio = "20-25%"
        emergency = "预留6-9个月生活费"
        advice = "结构性机会，但需谨慎"
    elif phase == "温和回暖":
        cash_ratio = "15-20%"
        fixed_ratio = "30-35%"
        risk_ratio = "25-30%"
        emergency = "预留6个月生活费"
        advice = "可以增加风险资产配置"
    else:
        cash_ratio = "25%"
        fixed_ratio = "40%"
        risk_ratio = "15%"
        emergency = "预留12个月生活费"
        advice = "保守稳健"
    
    savings = profile.get("savings", 250000)
    monthly_expense = profile.get("fixed_cost", 12000)
    if savings < monthly_expense * 12:
        emergency = "建议先积累应急金至12个月生活费"
        advice = "首要任务是积累应急金"
    
    return {
        "cash": cash_ratio,
        "fixed": fixed_ratio,
        "risk": risk_ratio,
        "emergency": emergency,
        "summary": advice
    }

def output():
    profile = load_profile()
    macro = analyze_macro()
    advice = family_advice(profile, macro)
    
    strategy = "稳健偏保守" if macro['phase'] in ["弱修复"] else ("保守" if macro['phase'] in ["偏弱"] else "平衡")
    
    print("="*50)
    print("📊 宏观 / 家庭理财简报")
    print("")
    print(f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("数据模式：V1简化版")
    print()
    
    print("一、当前宏观判断")
    print(f"- 当前阶段：{macro['phase']}")
    print(f"- 一句话结论：{macro['conclusion']}")
    print(f"- 主要依据：{macro['basis']}")
    print()
    
    print("二、家庭理财建议")
    print(f"- 现金建议：{advice['cash']}")
    print(f"- 定存/固收建议：{advice['fixed']}")
    print(f"- 风险资产建议：{advice['risk']}")
    print(f"- 应急金建议：{advice['emergency']}")
    print()
    
    print("三、今日结论")
    print(f"- 当前家庭策略：{strategy}")
    print(f"- 一句话建议：{advice['summary']}")
    print()
    print("="*50)

def main():
    output()

if __name__ == "__main__":
    main()
