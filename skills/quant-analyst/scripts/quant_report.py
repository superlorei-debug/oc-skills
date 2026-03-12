#!/usr/bin/env python3
"""
Quant Analyst - 量化策略分析脚本
"""
import json
from datetime import datetime

STATE_FILE = "/tmp/binance-spot-grid-bot/state_v2.json"

def load_state():
    with open(STATE_FILE) as f:
        return json.load(f)

def analyze(d):
    # 基本数据
    btc_price = d.get("anchor_price", 0)
    cash = d.get("paper_quote_balance", 0)
    btc_holdings = d.get("paper_base_balance", 0)
    pnl_today = d.get("today_pnl_quote", 0)
    pnl_yesterday = d.get("yesterday_pnl_quote", None)
    orders = d.get("open_buy_orders", [])
    
    # 策略参数
    total_u = 5000  # 策略总U数
    max_layers = 6  # 库存上限
    
    # 计算
    position_value = btc_holdings * btc_price  # 持仓占用U
    order_value = sum(o.get("total", 0) for o in orders)  # 挂单占用U
    used_u = position_value + order_value  # 已用U数合计
    remaining_u = total_u - used_u  # 剩余U数
    utilization = (used_u / total_u) * 100 if total_u > 0 else 0  # 资金利用率
    
    # 挂单价格列表
    order_prices = []
    for o in orders:
        price = o.get("price", 0)
        if price > 0:
            order_prices.append(price)
    order_prices.sort(reverse=True)
    
    current_layers = len(orders)  # 当前库存层数
    
    # 风控判断
    risks = []
    actions = []
    
    # 检查挂单层数
    if current_layers >= max_layers:
        status = "critical"
        status_cn = "危险"
        conclusion = f"库存层数已到 {current_layers}/{max_layers}，已打满，立即暂停新开仓"
        risks.append(f"库存层数{current_layers}已打满")
        actions.append("立即暂停新开仓")
    elif current_layers >= 4:
        status = "warning"
        status_cn = "预警"
        conclusion = f"库存层数已到 {current_layers}/{max_layers}，接近上限，暂时不建议激进加仓"
        risks.append(f"库存层数{current_layers}接近上限{max_layers}")
        actions.append("关注加仓节奏，避免满仓")
    else:
        status = "ok"
        status_cn = "正常"
        conclusion = "库存层数适中，策略正常运行"
        actions.append("继续观察")
    
    # 检查资金利用率
    if utilization > 85:
        status = "critical"
        status_cn = "危险"
        conclusion = f"资金利用率{utilization:.1f}%超限，请立即降仓"
        risks.append(f"资金利用率{utilization:.1f}%超限")
        actions.append("降低仓位")
    elif utilization > 70:
        if status == "ok":
            status = "warning"
            status_cn = "预警"
            conclusion = f"资金利用率{utilization:.1f}%偏高，注意控制"
        risks.append(f"资金利用率{utilization:.1f}%偏高")
    
    # 检查日亏损
    if pnl_today < -50:
        if status == "ok":
            status = "warning"
            status_cn = "预警"
        conclusion = f"日亏损{pnl_today:.2f}U，触发预警"
        risks.append(f"日亏损{pnl_today:.2f}U")
    
    # 生成输出
    lines = []
    lines.append("📈 量化策略")
    lines.append("")
    lines.append("币种：BTC")
    lines.append(f"当前价格：${btc_price:,.0f}")
    lines.append(f"当前持仓：{btc_holdings:.4f} BTC")
    lines.append(f"当前库存层数：{current_layers} / {max_layers}")
    lines.append("")
    lines.append(f"策略总U数：{total_u} U")
    lines.append(f"已持仓占用：{position_value:.0f} U")
    lines.append(f"挂单占用：{order_value:.0f} U")
    lines.append(f"已用U数合计：{used_u:.0f} U")
    lines.append(f"剩余U数：{remaining_u:.0f} U")
    lines.append(f"U上限：{total_u} U")
    lines.append("")
    
    # 挂单详情
    lines.append(f"买入挂单数量：{len(orders)}单")
    if order_prices:
        lines.append("买入挂单价格：")
        for i, p in enumerate(order_prices, 1):
            lines.append(f"  {i}. {p:,.0f}")
    else:
        lines.append("买入挂单价格：暂无")
    lines.append("")
    
    # 盈亏
    lines.append(f"今日盈亏：{pnl_today:+.2f} U")
    if pnl_yesterday is not None:
        lines.append(f"昨日盈亏：{pnl_yesterday:+.2f} U")
    else:
        lines.append("昨日盈亏：暂无数据")
    lines.append("")
    
    # 资金利用率
    lines.append(f"资金利用率：{utilization:.1f}%")
    lines.append("")
    
    # 状态
    lines.append(f"当前状态：{status} ({status_cn})")
    lines.append(f"一句话结论：{conclusion}")
    lines.append("")
    
    # 风险提示
    lines.append("风险提示：")
    if risks:
        for r in risks:
            lines.append(f"- {r}")
    else:
        lines.append("- 暂无明显风险")
    lines.append("")
    
    # 建议动作
    lines.append("建议动作：")
    if actions:
        for a in actions:
            lines.append(f"- {a}")
    else:
        lines.append("- 保持当前参数")
    
    return "\n".join(lines)

def main():
    print("="*50)
    print("📈 Quant Analyst - 量化策略分析")
    print("="*50)
    print()
    
    d = load_state()
    result = analyze(d)
    print(result)
    print()
    print("="*50)

if __name__ == "__main__":
    main()
