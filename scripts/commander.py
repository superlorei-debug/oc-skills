#!/usr/bin/env python3
"""
Commander - 主控汇总模块 V9
支持自然语言触发简版/详细版
"""
import subprocess
import json
import os
import sys
from datetime import datetime, timedelta
import re

HISTORY_DIR = "data/history/commander"

def detect_mode(user_input):
    """根据用户输入判断模式"""
    text = user_input.lower()
    
    # 检测部分展开（优先级最高）
    expand_news = any(k in text for k in ["新闻", "看看新闻", "新闻模块"])
    expand_macro = any(k in text for k in ["宏观", "理财", "家庭理财", "宏观模块"])
    expand_quant = any(k in text for k in ["量化", "策略", "交易", "网格"])
    
    if expand_news and not expand_macro and not expand_quant:
        return {"mode": "partial", "news": True, "macro": False, "quant": False}
    elif expand_macro and not expand_news and not expand_quant:
        return {"mode": "partial", "news": False, "macro": True, "quant": False}
    elif expand_quant and not expand_news and not expand_macro:
        return {"mode": "partial", "news": False, "macro": False, "quant": True}
    
    # 检测是否详细版
    detail_keywords = [
        "详细版", "详细看看", "展开新闻", "展开宏观", 
        "详细", "展开", "完整", "具体", "具体看看", "具体内容", "全部"
    ]
    
    has_detail_keyword = any(k in text for k in detail_keywords)
    
    if has_detail_keyword:
        return {"mode": "detail"}
    
    # 默认简版
    return {"mode": "simple"}

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
    data = {"mode": "无数据", "news": [], "time": datetime.now().strftime('%H:%M')}
    
    for line in out.split("\n"):
        if "当前模式：" in line:
            data["mode"] = line.split("：")[-1].strip()
        if "更新时间：" in line and "当前模式" not in line:
            data["time"] = line.split("：")[-1].strip()[:5]
    
    current_news = {}
    in_news = False
    for line in out.split("\n"):
        line = line.strip()
        if "---" in line and "新闻" not in line:
            if current_news and current_news.get("title"):
                data["news"].append(current_news)
            current_news = {}
            in_news = True
            continue
        if in_news:
            if "标题：" in line:
                current_news["title"] = line.split("：", 1)[-1].strip()
            elif "来源可信度：" in line:
                current_news["credibility"] = line.split("：")[-1].strip()
            elif "时间：" in line and "更新" not in line:
                current_news["date"] = line.split("：")[-1].strip()
            elif "核心内容：" in line:
                current_news["content"] = line.split("：", 1)[-1].strip()
            elif "市场影响：" in line:
                current_news["impact"] = line.split("：", 1)[-1].strip()
            elif "对BTC/量化策略的意义：" in line:
                current_news["meaning"] = line.split("：", 1)[-1].strip()
    
    if current_news and current_news.get("title"):
        data["news"].append(current_news)
    
    return data

def parse_macro():
    out, _ = run_cmd("scripts/macro_report.py")
    data = {"phase": "未知", "phase_def": "", "reasons": [], "strategy": "稳健", "strategy_def": "", "implications": [], "advice": "无", "time": datetime.now().strftime('%H:%M')}
    current_section = ""
    for line in out.split("\n"):
        line = line.strip()
        if "当前阶段：" in line and "定义" not in line:
            data["phase"] = line.split("：")[-1].strip()
        elif "当前阶段定义：" in line:
            data["phase_def"] = line.split("：")[-1].strip()
        elif "为什么是这个阶段：" in line:
            current_section = "reasons"
        elif current_section == "reasons" and line.startswith("-"):
            data["reasons"].append(line.replace("-", "").strip())
        elif "家庭策略：" in line and "定义" not in line:
            data["strategy"] = line.split("：")[-1].strip()
        elif "家庭策略定义：" in line:
            data["strategy_def"] = line.split("：")[-1].strip()
        elif "对我现在意味着什么：" in line:
            current_section = "implications"
        elif current_section == "implications" and line.startswith("-"):
            data["implications"].append(line.replace("-", "").strip())
        elif "一句话建议：" in line:
            data["advice"] = line.split("：")[-1].strip()
        elif "更新时间：" in line:
            data["time"] = line.split("：")[-1].strip()[:5]
    
    return data

def main(user_input=""):
    # 检测模式
    mode_info = detect_mode(user_input)
    mode = mode_info["mode"]
    
    # 部分展开模式
    partial = mode_info.get("mode") == "partial"
    expand_news = mode_info.get("news", False)
    expand_macro = mode_info.get("macro", False)
    expand_quant = mode_info.get("quant", False)
    
    q = parse_quant()
    n = parse_news()
    m = parse_macro()
    
    try:
        pnl = float(q.get("pnl", "0"))
        save_daily_summary(q.get("status"), n.get("mode"), m.get("phase"), "待定", pnl)
    except: pass
    
    yesterday = load_yesterday()
    if yesterday:
        if yesterday.get("quant_status") != q.get("status"):
            risk_change = "风险上升" if q.get("status") == "预警" else ("风险下降" if q.get("status") == "正常" else "风险上升")
        else:
            risk_change = "无明显变化"
    else:
        risk_change = "无昨日数据"
    
    print("="*50)
    print("📋 今日总览")
    if mode == "detail" or partial:
        print("(详细版)" if not partial else f"({['新闻','宏观','量化'][int(expand_macro)*2+int(expand_quant)]}详情)")
    print("="*50)
    print()
    
    # 判断是否展开量化（简版不展开）
    show_quant_detail = (mode == "detail") or expand_quant
    
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
    show_news_detail = (mode == "detail") or expand_news
    
    print("二、新闻影响")
    print(f"- 更新时间：{n['time']}")
    print(f"- 当前模式：{n['mode']}")
    print()
    
    if n['mode'] in ["实时模式", "缓存模式"] and n.get("news"):
        news_list = n.get("news", [])
        
        if show_news_detail:
            for i, news in enumerate(news_list[:3], 1):
                title = news.get('title', '无')[:60]
                content = news.get('content', '暂无')
                impact = news.get('impact', '暂无')
                meaning = news.get('meaning', '暂无')
                credibility = news.get('credibility', '低')
                
                print(f"{i}. 新闻标题：{title}")
                print(f"   - 核心内容：{content}")
                print(f"   - 市场影响：{impact}")
                print(f"   - 对BTC/量化策略的意义：{meaning}")
                print(f"   - 来源可信度：{credibility}")
                print()
            
            if len(news_list) > 3:
                print(f"其余{len(news_list)-3}条略")
                print()
        else:
            high_count = len([n for n in news_list if n.get('credibility') == '高'])
            print(f"- {len(news_list)}条新闻（{high_count}条高可信）")
            if any("approval" in n.get('title','').lower() for n in news_list):
                print("- 主要是银行申请审批，无重大政策变化")
            print()
    else:
        print("- 当前新闻模块未获取到有效实时新闻，本次判断暂不纳入新闻因素")
        print()
    
    # 三、宏观
    show_macro_detail = (mode == "detail") or expand_macro
    
    print("三、宏观 / 家庭理财")
    print(f"- 更新时间：{m['time']}")
    print()
    
    if show_macro_detail:
        print(f"1. 当前阶段：{m['phase']}")
        print()
        print(f"2. 当前阶段定义：{m['phase_def']}")
        print()
        print(f"3. 为什么是这个阶段：")
        for reason in m.get('reasons', [])[:3]:
            print(f"   - {reason}")
        print()
        print(f"4. 家庭策略：{m['strategy']}")
        print()
        print(f"5. 家庭策略定义：{m['strategy_def']}")
        print()
        print(f"6. 对我现在意味着什么：")
        for impl in m.get('implications', [])[:4]:
            print(f"   - {impl}")
        print()
        print(f"7. 一句话建议：{m['advice']}")
        print()
    else:
        print(f"- 当前阶段：{m['phase']}")
        print(f"- 家庭策略：{m['strategy']}")
        print(f"- 一句话建议：{m['advice']}")
        print()
    
    # 四、总判断
    print("四、总判断")
    
    news_valid = n['mode'] in ["实时模式", "缓存模式"] and n.get("news")
    has_risk = news_valid and any("利空" in n.get('title','') or "承压" in str(n) for n in n.get("news", []))
    
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
    
    if q['status'] == "危险" or (not news_valid and q['status'] == "预警"):
        basis = "以量化模块为主"
    elif has_risk:
        basis = "以新闻模块为主"
    elif m['strategy'] in ["保守", "稳健偏保守"]:
        basis = "以宏观模块为主"
    else:
        basis = "综合判断"
    
    news_note = "" if news_valid else "（本次总判断暂不纳入新闻因素）"
    
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
    user_input = sys.argv[1] if len(sys.argv) > 1 else ""
    main(user_input)
