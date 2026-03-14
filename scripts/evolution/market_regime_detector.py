#!/usr/bin/env python3
"""
Market Regime Detector - 市场状态识别
V1 先做粗颗粒度分类

输出: data/evolution/market_regime.json
"""
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/Users/mac/.openclaw/workspace/openclaw-project/runs/grid_bot/.env')

DATA_DIR = "/Users/mac/.openclaw/workspace/openclaw-project/data"
LATEST_DIR = f"{DATA_DIR}/latest"
EVOLUTION_DIR = f"{DATA_DIR}/evolution"

# 市场状态分类
REGIMES = {
    "震荡": {
        "description": "价格在一定区间内波动，无明显趋势",
        "suitable_params": ["正常网格间距", "中等仓位"],
    },
    "上行": {
        "description": "价格整体呈上涨趋势",
        "suitable_params": ["缩小网格间距", "适当增加持仓"],
    },
    "下行": {
        "description": "价格整体呈下跌趋势",
        "suitable_params": ["加大网格间距", "减少持仓"],
    },
    "高波动": {
        "description": "价格波动剧烈，风险较高",
        "suitable_params": ["加大网格间距", "降低单笔仓位", "提高止损阈值"],
    },
    "风险事件": {
        "description": "存在重大风险事件，市场可能剧烈波动",
        "suitable_params": ["暂停新开仓", "收紧止损", "降低整体仓位"],
    },
    "稳定": {
        "description": "价格波动较小，市场相对平稳",
        "suitable_params": ["正常网格", "正常仓位"],
    },
}

def load_data():
    """加载数据"""
    data = {}
    
    for fname in ['quant_report.json', 'news_report.json', 'macro_report.json']:
        try:
            with open(f"{LATEST_DIR}/{fname}") as f:
                key = fname.replace('.json', '').replace('_report', '')
                data[key] = json.load(f)
        except:
            pass
    
    return data

def detect_regime():
    """检测市场状态"""
    data = load_data()
    
    # V1 简化规则
    # 1. 先检查新闻风险
    news = data.get("news", {})
    risk_level = news.get("risk_level", "低")
    
    if risk_level in ["高", "极高"]:
        regime = "风险事件"
        confidence = 0.8
        reasons = [f"新闻风险等级: {risk_level}"]
        return build_result(regime, confidence, reasons)
    
    # 2. 检查宏观风险
    macro = data.get("macro", {})
    macro_stage = macro.get("stage", "")
    
    if "衰退" in macro_stage or "危机" in macro_stage:
        regime = "下行"
        confidence = 0.6
        reasons = [f"宏观阶段: {macro_stage}"]
        return build_result(regime, confidence, reasons)
    
    # 3. 基于价格波动判断 (如果有历史数据)
    # V1 简化：基于当前持仓和挂单判断
    quant = data.get("quant", {})
    utilization = quant.get("capital_utilization_pct", 0)
    layers = quant.get("inventory_layers_used", 0)
    status = quant.get("status")
    
    if status != "ok":
        regime = "稳定"  # 异常时保守判断
        confidence = 0.5
        reasons = ["策略状态异常，保守判断"]
        return build_result(regime, confidence, reasons)
    
    # V1 简化判断逻辑
    if utilization > 50:
        regime = "高波动"
        confidence = 0.6
        reasons = [f"资金利用率较高: {utilization}%"]
    elif layers >= 4:
        regime = "震荡"
        confidence = 0.6
        reasons = [f"库存层数较多: {layers}层"]
    elif layers == 0 and utilization < 10:
        regime = "稳定"
        confidence = 0.5
        reasons = ["资金利用率低，库存为空"]
    else:
        regime = "震荡"
        confidence = 0.4
        reasons = ["默认判断"]
    
    return build_result(regime, confidence, reasons)

def build_result(regime, confidence, reasons):
    """构建结果"""
    regime_info = REGIMES.get(regime, REGIMES["稳定"])
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "regime": regime,
        "confidence": confidence,
        "description": regime_info["description"],
        "suitable_params": regime_info["suitable_params"],
        "reasons": reasons,
    }
    
    return result

def save_result(result):
    """保存结果"""
    os.makedirs(EVOLUTION_DIR, exist_ok=True)
    
    with open(f"{EVOLUTION_DIR}/market_regime.json", 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    result = detect_regime()
    save_result(result)
    
    print("=" * 50)
    print(f"🌡️ 市场状态检测")
    print("=" * 50)
    print(f"当前状态: {result['regime']}")
    print(f"置信度: {result['confidence']*100:.0f}%")
    print(f"描述: {result['description']}")
    print("-" * 50)
    print("判断理由:")
    for r in result['reasons']:
        print(f"  • {r}")
    print("-" * 50)
    print("适合参数:")
    for p in result['suitable_params']:
        print(f"  • {p}")
    print("=" * 50)
    print(f"\n✅ 已保存到: {EVOLUTION_DIR}/market_regime.json")
