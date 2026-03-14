#!/usr/bin/env python3
"""
News - 新闻模块 V3
支持今日新闻识别和专业风险评估
"""
import requests
import json
import os
import time
import re
from datetime import datetime, timezone

CACHE_FILE = "data/cache/news_cache.json"
CACHE_MINUTES = 10

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                data = json.load(f)
            if time.time() - data.get("ts", 0) < CACHE_MINUTES * 60:
                return data.get("news", [])
        except:
            pass
    return None

def save_cache(news_list):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump({"ts": time.time(), "news": news_list}, f)
    except:
        pass

SOURCES = [
    {"name": "Federal Reserve", "url": "https://www.federalreserve.gov/feeds/press_all.xml", "credibility": "高", "category": "美联储"},
    {"name": "SEC Newsroom", "url": "https://www.sec.gov/news/pressreleases.rss.xml", "credibility": "高", "category": "美国监管"},
    {"name": "CoinDesk", "url": "https://www.coindesk.com/feed/", "credibility": "中", "category": "加密媒体"}
]

def parse_rss_date(date_str):
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str.replace("GMT", "+0000"), "%a, %d %b %Y %H:%M:%S %z")
        return dt.date()
    except:
        return None

def is_today(date_str):
    news_date = parse_rss_date(date_str)
    if not news_date:
        return False
    return news_date == datetime.now(timezone.utc).date()

def get_risk_level(news_list):
    today_news = [n for n in news_list if n.get("is_today", False)]
    high_risk_kw = ["war", "conflict", "attack", "sanction", "crash", "fed", "rate", "inflation", "sec", "regulation"]
    
    high_risk_count = 0
    for news in today_news:
        title = news.get("title", "").lower()
        content = news.get("core_content", "").lower()
        for k in high_risk_kw:
            if k in title or k in content:
                high_risk_count += 1
                break
    
    return "warning" if high_risk_count >= 2 else "normal"

def generate_summary(news_list):
    today_news = [n for n in news_list if n.get("is_today", False)]
    if not today_news:
        return "今日暂无重要新闻"
    
    risk_kw = ["fed", "rate", "inflation", "sec", "regulation", "war", "conflict"]
    has_risk = any(any(k in n.get("title", "").lower() for k in risk_kw) for n in today_news)
    
    if has_risk:
        return "今日出现重要宏观政策新闻，需关注市场波动。"
    return "今日暂无重大宏观风险新闻"

def simple_summary(title):
    title = title.lower()
    if any(k in title for k in ["fed", "rate", "interest", "powell"]):
        return "美联储政策相关"
    elif any(k in title for k in ["sec", "approval", "etf"]):
        return "监管政策相关"
    elif any(k in title for k in ["inflation", "cpi", "ppi", "gdp"]):
        return "宏观经济数据"
    elif any(k in title for k in ["ban", "restrict", "china"]):
        return "监管动向"
    return "市场新闻"

def fetch_rss(url, source_name, credibility, category):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, timeout=10, headers=headers)
        if r.status_code != 200:
            return []
        
        items = []
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(r.content)
            for item in root.findall('.//item')[:5]:
                title = item.find('title')
                link = item.find('link')
                pub_date = item.find('pubDate')
                
                title_text = title.text if title is not None else "无标题"
                link_text = link.text if link is not None else ""
                date_text = pub_date.text if pub_date is not None else ""
                
                is_today_news = is_today(date_text)
                
                items.append({
                    "title": title_text[:150],
                    "source": source_name,
                    "credibility": credibility,
                    "category": category,
                    "link": link_text,
                    "published_at": date_text,
                    "is_today": is_today_news,
                    "core_content": simple_summary(title_text),
                    "market_impact": "",
                    "btc_strategy_impact": ""
                })
        except:
            pass
        return items
    except:
        return []

def fetch_news():
    cached = load_cache()
    if cached:
        for news in cached:
            news["is_today"] = is_today(news.get("published_at", ""))
        return cached, "缓存模式"
    
    all_news = []
    for source in SOURCES:
        try:
            news = fetch_rss(source["url"], source["name"], source["credibility"], source["category"])
            all_news.extend(news)
            time.sleep(0.5)
        except:
            pass
    
    if all_news:
        for news in all_news:
            news["is_today"] = is_today(news.get("published_at", ""))
        save_cache(all_news)
        return all_news, "实时模式"
    
    return [], "无数据"

def format_output():
    news, mode = fetch_news()
    
    # 统计
    today_news = [n for n in news if n.get("is_today", False)]
    today_high = len([n for n in today_news if n.get("credibility") == "高"])
    
    risk_level = get_risk_level(news)
    summary = generate_summary(news)
    
    print("="*50)
    print("📰 新闻简报")
    print("="*50)
    print()
    print(f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"当前模式：{mode}")
    print()
    print(f"今日新闻：{len(today_news)}条")
    print(f"高可信今日：{today_high}条")
    print(f"风险等级：{risk_level}")
    print(f"摘要：{summary}")
    print()
    
    if today_news:
        print("--- 今日新闻 ---")
        for i, item in enumerate(today_news[:3], 1):
            print(f"{i}. {item.get('title', '')[:60]}")
            print(f"   来源：{item.get('source', '')} ({item.get('credibility', '')})")
    else:
        print("今日暂无重要新闻")
    
    print()
    print("="*50)

def generate_json():
    """生成 JSON 报告"""
    news, mode = fetch_news()
    
    # 统计
    today_news = [n for n in news if n.get("is_today", False)]
    today_high = len([n for n in today_news if n.get("credibility") == "高"])
    total_fetched = len(news)
    
    risk_level = get_risk_level(news)
    summary = generate_summary(news)
    
    # 判断状态
    if mode == "无数据" or total_fetched == 0:
        fetch_status = "抓取失败"
    elif len(today_news) == 0:
        fetch_status = "过滤后为空"
    else:
        fetch_status = "正常"
    
    result = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "fetch_mode": mode,
        "fetch_status": fetch_status,
        "total_fetched": total_fetched,
        "today_news_count": len(today_news),
        "high_cred_today_count": today_high,
        "risk_level": risk_level,
        "summary": summary,
        "status_detail": f"原始抓取 {total_fetched} 条，过滤后 {len(today_news)} 条" if total_fetched > 0 else "抓取失败，请检查网络或 RSS 源",
        "today_news": today_news[:5],
        "recent_news": news[:10]
    }
    
    return result

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        print(json.dumps(generate_json(), ensure_ascii=False, indent=2))
    else:
        format_output()
