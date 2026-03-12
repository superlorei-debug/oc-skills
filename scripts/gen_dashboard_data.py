#!/usr/bin/env python3
"""
生成看板数据 V3
数值字段用number，状态枚举统一，展示层再格式化
"""
import subprocess
import json
import os
import re
from datetime import datetime

DATA_DIR = "data/latest"
os.makedirs(DATA_DIR, exist_ok=True)

def run_cmd(path):
    try:
        r = subprocess.run(["python3", path], capture_output=True, text=True, timeout=15)
        return r.stdout
    except:
        return ""

# 1. 量化数据
print("生成量化数据...")
quant_out = run_cmd("scripts/quant_report.py")

quant_data = {
    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "symbol": "BTC",
    "price_usd": 0,
    "position_btc": 0.0,
    "inventory_layers_used": 0,
    "inventory_layers_limit": 6,
    "total_u": 0,
    "used_u": 0,
    "remaining_u": 0,
    "capital_utilization_pct": 0.0,
    "open_orders_count": 0,
    "today_pnl_u": 0.0,
    "yesterday_pnl_u": 0.0,
    "status": "ok",
    "risk_reason": "",
    "top_action": ""
}

in_risk = False
in_action = False

for line in quant_out.split("\n"):
    line_stripped = line.strip()
    
    if "当前价格：" in line:
        val = line.split("：")[-1].replace("$","").replace(",","").strip()
        try:
            quant_data["price_usd"] = float(val)
        except:
            quant_data["price_usd"] = 0
    elif "当前持仓：" in line:
        val = line.split("：")[-1].replace("BTC","").strip()
        try:
            quant_data["position_btc"] = float(val)
        except:
            quant_data["position_btc"] = 0.0
    elif "当前库存层数：" in line:
        match = re.search(r"(\d+)\s*/\s*(\d+)", line)
        if match:
            quant_data["inventory_layers_used"] = int(match.group(1))
            quant_data["inventory_layers_limit"] = int(match.group(2))
    elif "策略总U数：" in line:
        val = line.split("：")[-1].replace("U","").strip()
        try:
            quant_data["total_u"] = int(val)
        except:
            quant_data["total_u"] = 0
    elif "已持仓占用：" in line:
        val = line.split("：")[-1].replace("U","").strip()
        try:
            quant_data["used_u"] = int(val)
        except:
            quant_data["used_u"] = 0
    elif "剩余U数：" in line:
        val = line.split("：")[-1].replace("U","").strip()
        try:
            quant_data["remaining_u"] = int(val)
        except:
            quant_data["remaining_u"] = 0
    elif "资金利用率：" in line:
        val = line.split("：")[-1].replace("%","").strip()
        try:
            quant_data["capital_utilization_pct"] = float(val)
        except:
            quant_data["capital_utilization_pct"] = 0.0
    elif "今日盈亏：" in line:
        val = line.split("：")[-1].replace("U","").replace("+","").strip()
        try:
            quant_data["today_pnl_u"] = float(val)
        except:
            quant_data["today_pnl_u"] = 0.0
    elif "昨日盈亏：" in line:
        val = line.split("：")[-1].replace("U","").replace("+","").strip()
        try:
            quant_data["yesterday_pnl_u"] = float(val) if val and val != "暂无数据" else 0.0
        except:
            quant_data["yesterday_pnl_u"] = 0.0
    elif "当前状态：" in line:
        status = line.split("：")[-1].strip()
        if "危险" in status or "critical" in status.lower():
            quant_data["status"] = "critical"
        elif "预警" in status or "warning" in status.lower():
            quant_data["status"] = "warning"
        else:
            quant_data["status"] = "ok"
    elif "风险提示：" in line:
        in_risk = True
    elif in_risk and line_stripped.startswith("-"):
        quant_data["risk_reason"] = line_stripped.replace("-","").strip()
        in_risk = False
    elif "建议动作：" in line:
        in_action = True
    elif in_action and line_stripped.startswith("-"):
        quant_data["top_action"] = line_stripped.replace("-","").strip()
        in_action = False

order_match = re.search(r"买入挂单数量：(\d+)", quant_out)
if order_match:
    quant_data["open_orders_count"] = int(order_match.group(1))

with open(f"{DATA_DIR}/quant_report.json", "w") as f:
    json.dump(quant_data, f, ensure_ascii=False, indent=2)

# 2. 新闻数据
print("生成新闻数据...")
news_out = run_cmd("scripts/news_report.py")

news_data = {
    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "fetch_mode": "none",
    "total_count": 0,
    "high_cred_count": 0,
    "articles": []
}

mode_match = re.search(r"当前模式：(\S+)", news_out)
if mode_match:
    news_data["fetch_mode"] = mode_match.group(1)

current_article = {}
in_article = False

for line in news_out.split("\n"):
    line_stripped = line.strip()
    if "---" in line_stripped and "新闻" not in line_stripped:
        if current_article and current_article.get("title"):
            news_data["articles"].append(current_article)
        current_article = {}
        in_article = True
    elif in_article:
        if "标题：" in line:
            current_article["title"] = line.split("：", 1)[-1].strip()
        elif "来源可信度：" in line:
            current_article["credibility"] = line.split("：")[-1].strip()
        elif "时间：" in line and "更新" not in line:
            current_article["published_at"] = line.split("：")[-1].strip()
        elif "核心内容：" in line:
            current_article["core_content"] = line.split("：", 1)[-1].strip()
        elif "市场影响：" in line:
            current_article["market_impact"] = line.split("：", 1)[-1].strip()
        elif "对BTC" in line:
            current_article["btc_strategy_impact"] = line.split("：", 1)[-1].strip()
        elif "来源：" in line and "可信度" not in line:
            current_article["source"] = line.split("：")[-1].strip()

if current_article and current_article.get("title"):
    news_data["articles"].append(current_article)

news_data["total_count"] = len(news_data["articles"])
news_data["high_cred_count"] = len([a for a in news_data["articles"] if a.get("credibility") == "高"])

with open(f"{DATA_DIR}/news_report.json", "w") as f:
    json.dump(news_data, f, ensure_ascii=False, indent=2)

# 3. 宏观数据
print("生成宏观数据...")
macro_out = run_cmd("scripts/macro_report.py")

macro_data = {
    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "macro_phase": "unknown",
    "macro_phase_definition": "",
    "judgement_reasons": [],
    "family_strategy": "",
    "family_strategy_definition": "",
    "implications": [],
    "one_line_advice": ""
}

current_section = ""
for line in macro_out.split("\n"):
    line_stripped = line.strip()
    if "当前阶段：" in line_stripped and "定义" not in line_stripped:
        macro_data["macro_phase"] = line_stripped.split("：")[-1].strip()
    elif "当前阶段定义：" in line_stripped:
        macro_data["macro_phase_definition"] = line_stripped.split("：")[-1].strip()
    elif "为什么是这个阶段：" in line_stripped:
        current_section = "reasons"
    elif current_section == "reasons" and line_stripped.startswith("-"):
        macro_data["judgement_reasons"].append(line_stripped.replace("-", "").strip())
    elif "家庭策略：" in line_stripped and "定义" not in line_stripped:
        macro_data["family_strategy"] = line_stripped.split("：")[-1].strip()
    elif "家庭策略定义：" in line_stripped:
        macro_data["family_strategy_definition"] = line_stripped.split("：")[-1].strip()
    elif "对我现在意味着什么：" in line_stripped:
        current_section = "implications"
    elif current_section == "implications" and line_stripped.startswith("-"):
        macro_data["implications"].append(line_stripped.replace("-", "").strip())
    elif "一句话建议：" in line_stripped:
        macro_data["one_line_advice"] = line_stripped.split("：")[-1].strip()

with open(f"{DATA_DIR}/macro_report.json", "w") as f:
    json.dump(macro_data, f, ensure_ascii=False, indent=2)

# 4. Commander 汇总
print("生成汇总数据...")

risk_score = 0
if quant_data.get("status") == "critical":
    risk_score += 3
elif quant_data.get("status") == "warning":
    risk_score += 2

if news_data.get("high_cred_count", 0) > 0:
    risk_score += 1

if risk_score >= 3:
    risk_level = "critical"
    overall_advice = "暂时保守"
elif risk_score >= 1:
    risk_level = "warning"
    overall_advice = "谨慎运行"
else:
    risk_level = "ok"
    overall_advice = "继续运行"

if quant_data.get("status") == "critical":
    judgement_basis = "以量化模块为主"
elif news_data.get("high_cred_count", 0) > 0:
    judgement_basis = "以新闻模块为主"
elif macro_data.get("family_strategy") in ["保守", "稳健偏保守"]:
    judgement_basis = "以宏观模块为主"
else:
    judgement_basis = "综合判断"

commander_data = {
    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "overall_risk_level": risk_level,
    "overall_advice": overall_advice,
    "judgement_basis": judgement_basis
}

with open(f"{DATA_DIR}/commander_summary.json", "w") as f:
    json.dump(commander_data, f, ensure_ascii=False, indent=2)

print("数据生成完成！")
