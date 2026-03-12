#!/usr/bin/env python3
"""
Dashboard 数据生成器
定期抓取各模块数据，生成 JSON 供前端展示
"""
import subprocess
import json
import os
from datetime import datetime

OUTPUT_FILE = "dashboard/data/dashboard.json"

def run_cmd(path):
    try:
        r = subprocess.run(["python3", path], capture_output=True, text=True, timeout=15)
        return r.stdout
    except:
        return ""

def parse_quant():
    out = run_cmd("scripts/quant_report.py")
    data = {}
    for line in out.split("\n"):
        if "当前价格：" in line:
            price = line.split("：")[-1].replace("$","").replace(",","").strip()
            data["price"] = int(price) if price.isdigit() else 0
        if "当前持仓：" in line:
            data["position"] = line.split("：")[-1].replace("BTC","").strip()
        if "今日盈亏：" in line:
            data["today_pnl"] = line.split("：")[-1].strip()
        if "资金利用率：" in line:
            data["utilization"] = line.split("：")[-1].strip()
        if "当前状态：" in line:
            status = line.split("：")[-1].strip()
            data["status"] = "危险" if "危险" in status else ("预警" if "预警" in status else "正常")
        if "库存层数" in line and "/" in line:
            data["grid_levels"] = line.split("：")[-1].strip()
    return data

def parse_news():
    out = run_cmd("scripts/news_report.py")
    articles = []
    current = {}
    in_news = False
    
    for line in out.split("\n"):
        if "---" in line and "新闻" not in line:
            if current.get("title"):
                articles.append(current)
            current = {}
            in_news = True
        elif in_news:
            if "标题：" in line:
                current["title"] = line.split("：", 1)[-1].strip()
            elif "时间：" in line and "更新" not in line:
                current["time"] = line.split("：")[-1].strip()
            elif "来源可信度：" in line:
                current["credibility"] = line.split("：")[-1].strip()
            elif "核心内容：" in line:
                current["content"] = line.split("：", 1)[-1].strip()
            elif "市场影响：" in line:
                current["impact"] = line.split("：", 1)[-1].strip()
            elif "对BTC/量化策略的意义：" in line:
                current["btc_meaning"] = line.split("：", 1)[-1].strip()
                current["source"] = "Federal Reserve"
    
    if current.get("title"):
        articles.append(current)
    
    return {
        "articles": articles,
        "total_count": len(articles),
        "high_cred_count": len([a for a in articles if a.get("credibility") == "高"])
    }

def parse_macro():
    out = run_cmd("scripts/macro_report.py")
    data = {}
    section = ""
    
    for line in out.split("\n"):
        line = line.strip()
        if "当前阶段：" in line and "定义" not in line:
            data["phase"] = line.split("：")[-1].strip()
        elif "当前阶段定义：" in line:
            data["phase_definition"] = line.split("：")[-1].strip()
        elif "家庭策略：" in line and "定义" not in line:
            data["strategy"] = line.split("：")[-1].strip()
        elif "家庭策略定义：" in line:
            data["strategy_definition"] = line.split("：")[-1].strip()
        elif "一句话建议：" in line:
            data["advice"] = line.split("：")[-1].strip()
        elif line.startswith("-"):
            if "reasons" not in data:
                data["reasons"] = []
            if "理由" in section:
                data["reasons"].append(line.replace("-","").strip())
            elif "意味着" in section:
                if "implications" not in data:
                    data["implications"] = []
                data["implications"].append(line.replace("-","").strip())
        elif "为什么是这个阶段" in line:
            section = "reasons"
        elif "对我现在意味着什么" in line:
            section = "implications"
    
    return data

def generate():
    print("生成 Dashboard 数据...")
    
    quant = parse_quant()
    news = parse_news()
    macro = parse_macro()
    
    # 计算总览
    risk_level = "低"
    overall_advice = "继续运行"
    
    if quant.get("status") == "危险":
        risk_level = "高"
        overall_advice = "暂时保守"
    elif quant.get("status") == "预警":
        risk_level = "中"
        overall_advice = "谨慎运行"
    
    data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "overview": {
            "risk_level": risk_level,
            "overall_advice": overall_advice,
            "quant_status": quant.get("status", "未知"),
            "quant_pnl": quant.get("today_pnl", "0"),
            "basis": "以量化模块为主",
            "news_mode": "实时模式" if news.get("total_count", 0) > 0 else "无数据"
        },
        "quant": {
            "symbol": "BTC",
            "price": quant.get("price", 0),
            "position": quant.get("position", "0"),
            "total_u": 5000,
            "used_u": 2232,
            "remaining_u": 2768,
            "utilization": quant.get("utilization", "0%"),
            "grid_levels": quant.get("grid_levels", "0/6"),
            "open_orders": 6,
            "today_pnl": quant.get("today_pnl", "0"),
            "yesterday_pnl": "暂无数据",
            "status": quant.get("status", "未知"),
            "risk_reason": "库存层数已打满" if "/" in str(quant.get("grid_levels","")) else "无",
            "action": "立即暂停新开仓" if quant.get("status") == "危险" else "保持观察"
        },
        "news": news,
        "macro": macro
    }
    
    # 写入文件
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"已生成: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate()
