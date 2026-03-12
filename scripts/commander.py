#!/usr/bin/env python3
"""
Commander - 主控汇总模块 V4
整合量化 + 新闻 + 宏观 + 历史对比 + 定时推送
"""
import subprocess
import json
import os
from datetime import datetime, timedelta

HISTORY_DIR = "data/history/commander"

def get_today_file():
    return f"{HISTORY_DIR}/{datetime.now().strftime('%Y-%m-%d')}.json"

def get_yesterday_file():
    yesterday = datetime.now() - timedelta(days=1)
    return f"{HISTORY_DIR}/{yesterday.strftime('%Y-%m-%d')}.json"

def save_daily_summary(quant_status, news_mode, macro_phase, overall, pnl):
    os.makedirs(HISTORY_DIR, exist_ok=True)
    data = {
        "date": datetime.now().strftime('%Y-%m-%d'),
        "quant_status": quant_status,
        "quant_pnl": pnl,
        "news_mode": news_mode,
        "macro_phase": macro_phase,
        "overall": overall,
    }
    with open(get_today_file(), "w") as f:
        json.dump(data, f)

def load_yesterday():
    f = get_yesterday_file()
    if os.path.exists(f):
        with open(f) as f:
            return json.load(f)
    return None

def run_cmd(path):
    try:
        r = subprocess.run(["python3", path], capture_output=True, text=True, timeout=15)
        return r.stdout
    except: return ""

def parse_quant():
    out = run_cmd("/Users/mac/.openclaw/workspace/skills/quant-analyst/scripts/quant_report.py")
    data = {"status": "未知", "pnl": "0", "util": "0%", "risk": "无", "action": "保持观察"}
    in_risk = False
    in_action = False
    for line in out.split("\n"):
        if "当前状态：" in line:
            if "预警" in line: data["status"] = "预警"
            elif "危险" in line: data["status"] = "危险"
            else: data["status"] = "正常"
        if "今日盈亏：" in line:
            data["pnl"] = line.split("：")[-1].replace("U","").replace("+","").strip()
        if "资金利用率：" in line:
            data["util"] = line.split("：")[-1].strip()
        if "风险提示：" in line:
            in_risk = True
            continue
        if in_risk and line.strip().startswith("-"):
            data["risk"] = line.strip().replace("-","").strip()
            in_risk = False
        if "建议动作：" in line:
            in_action = True
            continue
        if in_action and line.strip().startswith("-"):
            data["action"] = line.strip().replace("-","").strip()
            in_action = False
    return data

def parse_news():
    out = run_cmd("/Users/mac/.openclaw/workspace/skills/news-geopolitics/scripts/news_report.py")
    data = {"mode": "无数据", "event": "无", "impact": "无"}
    for line in out.split("\n"):
        if "当前模式：" in line:
            data["mode"] = line.split("：")[-1].strip()
        if "事件名称：" in line and data["event"] == "无":
            data["event"] = line.split("：")[-1].strip()[:30]
        if "一句话结论：" in line:
            data["impact"] = line.split("：")[-1].strip()
    return data

def parse_macro():
    out = run_cmd("/Users/mac/.openclaw/workspace/skills/macro-advisor/scripts/macro_report.py")
    data = {"phase": "未知", "strategy": "稳健", "advice": "无"}
    for line in out.split("\n"):
        if "当前阶段：" in line:
            data["phase"] = line.split("：")[-1].strip()
        if "当前家庭策略：" in line:
            data["strategy"] = line.split("：")[-1].strip()
        if "一句话建议：" in line:
            data["advice"] = line.split("：")[-1].strip()
    return data

def get_comparison():
    """获取对比"""
    yesterday = load_yesterday()
    if not yesterday:
        return None
    
    today_file = get_today_file()
    if not os.path.exists(today_file):
        return None
    
    with open(today_file) as f:
        today = json.load(f)
    
    changes = []
    
    # 量化对比
    if yesterday.get("quant_status") != today.get("quant_status"):
        changes.append(f"量化:{yesterday['quant_status']}→{today['quant_status']}")
    
    # 宏观对比
    if yesterday.get("macro_phase") != today.get("macro_phase"):
        changes.append(f"宏观:{yesterday['macro_phase']}→{today['macro_phase']}")
    
    return changes if changes else None

def main(show_detail=False):
    q = parse_quant()
    n = parse_news()
    m = parse_macro()
    
    # 保存今日摘要
    try:
        pnl = float(q.get("pnl", "0"))
        save_daily_summary(q.get("status"), n.get("mode"), m.get("phase"), "待定", pnl)
    except:
        pass
    
    # 对比
    compare = get_comparison()
    
    print("="*50)
    print("📋 今日总览")
    print("="*50)
    print()
    
    # 一、量化
    print("一、量化策略")
    print(f"- 状态：{q['status']}")
    print(f"- 今日盈亏：{q['pnl']} U")
    print(f"- 资金利用率：{q['util']}")
    print(f"- 风险提示：{q['risk']}")
    print(f"- 建议动作：{q['action']}")
    print()
    
    # 二、新闻
    print("二、新闻影响")
    print(f"- 当前模式：{n['mode']}")
    if n['mode'] in ["实时模式", "缓存模式"]:
        print(f"- 重要事件：{n['event']}")
    else:
        print("- 重要事件：新闻模块当前未获取到实时新闻，暂不纳入判断")
    print()
    
    # 三、宏观（简洁版）
    print("三、宏观/家庭理财")
    print(f"- 当前阶段：{m['phase']}")
    print(f"- 家庭策略：{m['strategy']}")
    print(f"- 一句话建议：{m['advice']}")
    print()
    
    # 四、历史对比
    if compare:
        print("四、对比昨天")
        for c in compare:
            print(f"- {c}")
        print()
    
    # 五、总判断
    print("四、总判断")
    
    news_valid = n['mode'] in ["实时模式", "缓存模式"]
    has_risk = news_valid and ("避险" in n.get('impact','') or "恐慌" in n.get('impact',''))
    
    risk_count = 0
    if q['status'] == "危险": risk_count += 2
    elif q['status'] == "预警": risk_count += 1
    if has_risk: risk_count += 1
    if m['strategy'] in ["保守", "稳健偏保守"]: risk_count += 1
    
    if risk_count >= 3:
        overall, basis = "暂时保守", "综合判断"
    elif q['status'] == "危险" or has_risk:
        overall, basis = "暂时保守", "以量化/新闻模块为主"
    elif q['status'] == "预警":
        overall, basis = "谨慎运行", "以量化模块为主"
    elif m['strategy'] in ["保守", "稳健偏保守"]:
        overall, basis = "谨慎运行", "以宏观模块为主"
    else:
        overall, basis = "继续运行", "综合判断"
    
    if overall == "暂时保守":
        advice = f"总体偏保守，{q['action']}"
    elif overall == "谨慎运行":
        advice = "控制风险，保持当前节奏"
    else:
        advice = "保持正常节奏"
    
    print(f"- 今天整体建议：{overall}")
    print(f"- 判断依据：{basis}")
    print(f"- {advice}")
    print()
    print("="*50)

if __name__ == "__main__":
    main()
