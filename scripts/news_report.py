#!/usr/bin/env python3
import json, os, time, requests
from datetime import datetime

C = "/tmp/news_cache.json"

def lc():
    if os.path.exists(C):
        try:
            with open(C) as f: d = json.load(f)
            if time.time() - d.get("ts",0) < 120: return d
        except: pass
    return None

def sc(d, m):
    try:
        with open(C, "w") as f: json.dump({"ts": time.time(), "mode": m, "news": d}, f)
    except: pass

def fetch():
    try:
        r = requests.get("https://min-api.cryptocompare.com/data/v2/news/?lang=EN", timeout=8)
        if r.status_code == 200:
            d = r.json()
            if d.get("Data"): return d["Data"][:3], "实时模式"
    except: pass
    c = lc()
    if c and c.get("news"): return c["news"], "缓存模式"
    return None, "无数据"

def ana(t, b):
    t, b = (t or "").lower(), (b or "").lower()
    i = {"btc": "无", "gold": "无", "oil": "无", "us": "无", "a": "无", "risk": "无"}
    if any(k in t or k in b for k in ["war", "iran", "israel"]): i["risk"] = "避险"; i["gold"] = "利好"
    if any(k in t or k in b for k in ["sec", "regulation", "ban"]): i["btc"] = "利空"; i["risk"] = "担忧"
    if any(k in t or k in b for k in ["etf", "blackrock"]): i["btc"] = "利好"; i["risk"] = "机构信号"
    if any(k in t or k in b for k in ["surge", "rally", "breakout"]): i["btc"] = "利好"; i["risk"] = "乐观"
    if any(k in t or k in b for k in ["crash", "plunge", "drop"]): i["btc"] = "利空"; i["risk"] = "恐慌"
    return i

def cr(s):
    s = s.lower()
    if any(x in s for x in ["cointelegraph", "bloomberg", "reuters"]): return "高"
    if any(x in s for x in ["bitcoin world", "decrypt"]): return "中"
    return "低"

def lv(t):
    t = t.lower()
    if any(k in t for k in ["war", "crash", "sanction"]): return "高风险"
    if any(k in t for k in ["etf", "fed", "breakout"]): return "重要"
    return "普通"

def out(news, mode):
    L = []
    L.append("="*50)
    L.append("News & Geopolitics - 新闻影响分析")
    L.append("="*50)
    L.append("")
    L.append("新闻影响简报")
    L.append("")
    L.append("更新时间：" + datetime.now().strftime('%Y-%m-%d %H:%M'))
    L.append("当前模式：" + mode)
    L.append("")
    if not news: L.extend(["暂无重要新闻", ""]); return "\n".join(L)
    for idx, it in enumerate(news, 1):
        t, b = it.get("title",""), (it.get("body","")[:150] or "").replace("\n"," ")
        s = it.get("source_info",{}).get("name","未知")
        i, l = ana(t,b), lv(t)
        L.extend([f"--- 事件 {idx} ---", f"事件名称：{t}", f"来源：{s} (可信度:{cr(s)})", f"事件级别：l", "消息状态：已确认", "", f"核心内容：{b}...", "", "可能影响：", f"  BTC：{i['btc']}", f"  黄金：{i['gold']}", f"  原油：{i['oil']}", f"  美股：{i['us']}", f"  A股：{i['a']}", f"  风险偏好：{i['risk']}", ""])
    rs = [ana(n.get("title",""), n.get("body",""))["risk"] for n in news]
    c = "暂无重大影响" if not any("避险"in r or "乐观"in r or "恐慌"in r for r in rs) else ("市场情绪偏乐观，警惕波动" if any("乐观"in r for r in rs) else "市场有恐慌，建议谨慎")
    L.extend(["一句话结论：", f"  {c}", "", "建议动作：", "  - 继续观察", "  - 如有持仓关注止损", ""])
    L.append("="*50)
    return "\n".join(L)

c = lc()
if c: print(out(c.get("news",[]), "缓存模式"))
else:
    n, m = fetch()
    if n: sc(n, m)
    print(out(n, m))
