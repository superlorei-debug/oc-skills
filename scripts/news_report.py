#!/usr/bin/env python3
"""
News - 免费新闻源方案 V2
"""
import requests
import json
import os
import time
import re
from datetime import datetime
from urllib.parse import urljoin

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

# ===== 数据源配置 =====
SOURCES = [
    {
        "name": "Federal Reserve",
        "url": "https://www.federalreserve.gov/feeds/press_all.xml",
        "credibility": "高",
        "category": "美联储"
    },
    {
        "name": "SEC Newsroom",
        "url": "https://www.sec.gov/news/pressreleases.rss.xml",
        "credibility": "高",
        "category": "美国监管"
    },
    {
        "name": "CoinDesk",
        "url": "https://www.coindesk.com/feed/",
        "credibility": "中",
        "category": "加密媒体"
    },
    {
        "name": "Binance",
        "url": "https://www.binance.com/en/support/announcement",
        "credibility": "高",
        "category": "交易所公告"
    }
]

def fetch_rss(url, source_name, credibility, category):
    """抓取 RSS 源"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, timeout=10, headers=headers)
        if r.status_code != 200:
            return []
        
        items = []
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(r.text)
            for item in root.findall('.//item')[:3]:
                title = item.find('title')
                link = item.find('link')
                pub_date = item.find('pubDate')
                
                title_text = title.text if title is not None else "无标题"
                link_text = link.text if link is not None else ""
                date_text = pub_date.text if pub_date is not None else ""
                
                # 生成摘要
                summary = generate_summary(title_text, category)
                
                items.append({
                    "title": title_text[:150],
                    "source": source_name,
                    "credibility": credibility,
                    "category": category,
                    "link": link_text,
                    "date": date_text[:30] if date_text else datetime.now().strftime("%Y-%m-%d"),
                    "summary": summary
                })
        except:
            pass
        
        return items
    except Exception as e:
        return []

def generate_summary(title, category):
    """根据标题生成摘要和影响分析"""
    title_lower = title.lower()
    
    # 关键词匹配
    if any(k in title_lower for k in ['fed', 'federal reserve', 'rate', 'interest', 'powell', 'fomc']):
        summary = "美联储政策相关消息"
        impact = "影响市场流动性预期"
    elif any(k in title_lower for k in ['sec', 'approval', 'etf', 'regulation']):
        summary = "监管政策消息"
        impact = "影响市场准入和预期"
    elif any(k in title_lower for k in ['inflation', 'cpi', 'ppi', 'gdp', 'employment']):
        summary = "宏观经济数据"
        impact = "影响政策预期"
    elif any(k in title_lower for k in ['china', 'chinese', 'pboc', 'yuan']):
        summary = "中国相关消息"
        impact = "影响市场情绪"
    elif any(k in title_lower for k in ['bitcoin', 'btc', 'crypto', 'ethereum']):
        summary = "加密货币消息"
        impact = "直接影响币价"
    else:
        summary = "市场新闻"
        impact = "需关注市场反应"
    
    return summary

def analyze_impact(title, category):
    """分析对市场和量化策略的影响"""
    title_lower = title.lower()
    
    market_impact = ""
    quant_meaning = ""
    
    if any(k in title_lower for k in ['fed', 'rate', 'interest', 'powell']):
        market_impact = "美联储政策预期变化，可能影响全球流动性"
        quant_meaning = "若偏鹰派，BTC可能承压，网格需警惕大幅波动"
    elif any(k in title_lower for k in ['sec', 'etf', 'approval']):
        market_impact = "监管政策利好/利空"
        quant_meaning = "若利好，BTC可能上涨；若利空，需警惕下跌"
    elif any(k in title_lower for k in ['inflation', 'cpi', 'ppi']):
        market_impact = "通胀数据影响政策预期"
        quant_meaning = "若通胀回升，降息预期降温，风险资产承压"
    elif any(k in title_lower for k in ['employment', 'jobs', 'unemployment']):
        market_impact = "就业数据影响经济预期"
        quant_meaning = "若就业强劲，避险需求下降，BTC可能承压"
    elif any(k in title_lower for k in ['china', 'pboc']):
        market_impact = "中国市场/政策消息"
        quant_meaning = "可能影响全球风险偏好"
    elif any(k in title_lower for k in ['ban', 'restrict', 'crackdown']):
        market_impact = "监管利空消息"
        quant_meaning = "短期风险厌恶上升，建议减仓或观望"
    else:
        market_impact = "常规新闻"
        quant_meaning = "暂时影响有限，继续观察"
    
    return market_impact, quant_meaning

def fetch_news():
    """抓取新闻"""
    cached = load_cache()
    if cached:
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
        save_cache(all_news)
        return all_news, "实时模式"
    
    return [], "无数据"

def format_output():
    news, mode = fetch_news()
    
    print("="*50)
    print("📰 新闻简报")
    print("="*50)
    print()
    print(f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"当前模式：{mode}")
    print()
    
    if not news:
        print("当前无新增高可信新闻")
        print()
        print("="*50)
        return
    
    # 按可信度排序
    priority = {"高": 0, "中": 1, "低": 2}
    news.sort(key=lambda x: priority.get(x.get("credibility", "低"), 2))
    
    for i, item in enumerate(news[:5], 1):
        title = item.get("title", "无标题")
        market_impact, quant_meaning = analyze_impact(title, item.get("category", ""))
        
        print(f"--- {i}. {item.get('source', '未知')} ({item.get('category', '')}) ---")
        print(f"标题：{title}")
        print(f"时间：{item.get('date', '')}")
        print(f"来源可信度：{item.get('credibility', '低')}")
        print(f"核心内容：{item.get('summary', '')}")
        print(f"市场影响：{market_impact}")
        print(f"对BTC/量化策略的意义：{quant_meaning}")
        print()
    
    print("="*50)

if __name__ == "__main__":
    format_output()
