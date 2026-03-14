#!/usr/bin/env python3
"""
Evolution Coordinator - 进化模块协调器
运行所有进化子模块
"""
import sys
import os

# 添加脚本目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trade_journal import record_trade_event, generate_summary as journal_summary
from strategy_evaluator import evaluate_strategy, save_result as save_strategy
from market_regime_detector import detect_regime, save_result as save_regime
from parameter_lab import generate_candidates, save_result as save_params
from evolution_main import evaluate_upgrade, save_result as save_upgrade

def run_all():
    """运行所有进化模块"""
    print("=" * 60)
    print("🚀 AI Quant Brain 自我进化模块 V1")
    print("=" * 60)
    print()
    
    # 1. 交易日志
    print("📝 1/5 交易日志...")
    summary = journal_summary()
    if summary:
        print(f"   记录事件: {summary.get('total_events', 0)}")
    else:
        print("   暂无记录")
    
    # 2. 策略评估
    print("📊 2/5 策略评估...")
    strategy = evaluate_strategy()
    save_strategy(strategy)
    print(f"   综合评分: {strategy['scores']['overall']}/100")
    
    # 3. 市场状态
    print("🌡️ 3/5 市场状态...")
    regime = detect_regime()
    save_regime(regime)
    print(f"   当前状态: {regime['regime']}")
    
    # 4. 参数建议
    print("🔬 4/5 参数实验室...")
    params = generate_candidates()
    save_params(params)
    print(f"   推荐方案: {params['recommended']}")
    
    # 5. 升级闸门
    print("🚪 5/5 升级闸门...")
    upgrade = evaluate_upgrade()
    save_upgrade(upgrade)
    print(f"   决策: {upgrade['decision']}")
    
    print()
    print("=" * 60)
    print("✅ 进化模块执行完成")
    print("=" * 60)
    print()
    print("输出文件:")
    print(f"  - data/evolution/trade_journal.json")
    print(f"  - data/evolution/strategy_score.json")
    print(f"  - data/evolution/market_regime.json")
    print(f"  - data/evolution/parameter_candidates.json")
    print(f"  - data/evolution/upgrade_decision.json")

if __name__ == "__main__":
    run_all()
