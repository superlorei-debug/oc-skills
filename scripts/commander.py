#!/usr/bin/env python3
"""
Commander - 主控汇总模块 V5
整合量化 + 新闻 + 宏观 + 历史对比
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

def get_risk_change():
    """对比昨日风险变化"""
    yesterday = load_yesterday()
    if not yesterday:
        return "无昨日数据"
    
    yesterday_status = yesterday.get("quant_status", "")
    
    # 简单判断
    if yesterday_status == "正常" and "预警" in str(get_today_file()):
        return "风险上升"
    elif yesterday_status == "预警" and "正常" in str(get_today_file()):
        return "风险下降"
    elif yesterday_status == "危险":
        return "风险上升"
    else:
        return "无明显变化"

def run_cmd(path):
    try:
        r = subprocess.run(["python3", path], capture_output=True, text=True, timeout=15)
        return r.stdout, r.stderr
    except: return "", ""

def parse_quant():
    out, _ = run_cmd("scripts/quant_report.py")
    data = {"status": "未知", "pnl": "0", "util": "0%", "risk": "无", "action": "保持观察", "time": datetime.now().strftime('%H:%M')}
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
    out, _ = run_cmd("scripts/news_report.py")
    data = {"mode": "无数据", "event": "无", "impact": "无", "time": datetime.now().strftime('%H:%M')}
    for line in out.split("\n"):
        if "当前模式：" in line:
            data["mode"] = line.split("：")[-1].strip()
        if "更新时间：" in line and "当前模式" not in line:
            data["time"] = line.split("：")[-1].strip()
        if "事件名称：" in line and data["event"] == "无":
            data["event"] = line.split("：")[-1].strip()[:30]
        if "一句话结论：" in line:
            data["impact"] = line.split("：")[-1].strip()
    return data

def parse_macro():
    out, _ = run_cmd("scripts/macro_report.py")
    data = {"phase": "未知", "strategy": "稳健", "advice": "无", "time": datetime.now().strftime('%H:%M')}
    for line in out.split("\n"):
        if "当前阶段：" in line:
            data["phase"] = line.split("：")[-1].strip()
        if "当前家庭策略：" in line:
            data["strategy"] = line.split("：")[-1].strip()
        if "一句话建议：" in line:
            data["advice"] = line.split("：")[-1].strip()
        if "更新时间：" in line:
            data["time"] = line.split("：")[-1].strip()[:5]
    return data

def main():
    q = parse_quant()
    n = parse_news()
    m = parse_macro()
    
    # 保存今日摘要
    try:
        pnl = float(q.get("pnl", "0"))
        save_daily_summary(q.get("status"), n.get("mode"), m.get("phase"), "待定", pnl)
    except:
        pass
    
    # 昨日对比
    yesterday = load_yesterday()
    if yesterday:
        if yesterday.get("quant_status") != q.get("status"):
            if q.get("status") == "预警":
                risk_change = "风险上升"
            elif q.get("status") == "正常":
                risk_change = "风险下降"
            else:
                risk_change = "风险上升"
        else:
            risk_change = "无明显变化"
    else:
        risk_change = "无昨日数据"
    
    print("="*50)
    print("📋 今日总览")
    print("="*50)
    print()
    
    # 一、量化
    print("一、量化策略")
    print(f"- 更新时间：{q['time']}")
    print(f"- 状态：{q['status']}")
    print(f"- 今日盈亏：{q['pnl']} U")
    print(f"- 资金利用率：{q['util']}")
    print(f"- 风险提示：{q['risk']}")
    print(f"- 建议动作：{q['action']}")
    print(f"- 相比昨日：{risk_change}")
    print()
    
    # 二、新闻
    print("二、新闻影响")
    print(f"- 更新时间：{n['time']}")
    print(f"- 当前模式：{n['mode']}")
    if n['mode'] in ["实时模式", "缓存模式"]:
        print(f"- 重要事件：{n['event']}")
    else:
        print("- 重要事件：新闻模块当前未获取到实时新闻，暂不纳入判断")
    print()
    
    # 三、宏观
    print("三、宏观/家庭理财")
    print(f"- 更新时间：{m['time']}")
    print(f"- 当前阶段：{m['phase']}")
    print(f"- 家庭策略：{m['strategy']}")
    print(f"- 一句话建议：{m['advice']}")
    print()
    
    # 四、总判断
    print("四、总判断")
    
    news_valid = n['mode'] in ["实时模式", "缓存模式"]
    has_risk = news_valid and ("避险" in n.get('impact','') or "恐慌" in n.get('impact',''))
    
    # 计算风险等级
    risk_score = 0
    if q['status'] == "危险": risk_score += 3
    elif q['status'] == "预警": risk_score += 2
    if has_risk: risk_score += 2
    if m['strategy'] in ["保守"]: risk_score += 1
    
    if risk_score >= 4:
        risk_level = "高"
        overall = "暂时保守"
    elif risk_score >= 2:
        risk_level = "中"
        overall = "谨慎运行"
    else:
        risk_level = "低"
        overall = "继续运行"
    
    # 判断依据
    if q['status'] == "危险" or (not news_valid and q['status'] == "预警"):
        basis = "以量化模块为主"
    elif has_risk:
        basis = "以新闻模块为主"
    elif m['strategy'] in ["保守", "稳健偏保守"]:
        basis = "以宏观模块为主"
    else:
        basis = "综合判断"
    
    # 新闻补充说明
    news_note = "" if news_valid else "（本次总判断暂不纳入新闻因素）"
    
    # 压缩建议
    if overall == "暂时保守":
        advice = f"总体偏保守，{q['action']}"
    elif overall == "谨慎运行":
        advice = "控制风险，保持当前节奏"
    else:
        advice = "保持正常节奏"
    
    print(f"- 总体风险等级：{risk_level}")
    print(f"- 今天整体建议：{overall}")
    print(f"- 判断依据：{basis} {news_note}")
    print(f"- {advice}")
    print()
    print("="*50)

if __name__ == "__main__":
    main()
