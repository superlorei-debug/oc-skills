#!/usr/bin/env python3
"""
News - 免费新闻源方案
"""
import requests
import json
import os
import time
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
        "name": "Binance Announcement",
        "url": "https://www.binance.com/en/support/announcement",
        "credibility": "高",
        "category": "交易所公告",
        "type": "html"
    },
    {
        "name": "SEC Newsroom",
        "url": "https://www.sec.gov/news/pressreleases.rss.xml",
        "credibility": "高",
        "category": "美国监管",
        "type": "rss"
    },
    {
        "name": "Federal Reserve",
        "url": "https://www.federalreserve.gov/feeds/press_all.xml",
        "credibility": "高",
        "category": "美联储",
        "type": "rss"
    },
    {
        "name": "CoinDesk",
        "url": "https://www.coindesk.com/feed/",
        "credibility": "中",
        "category": "加密媒体",
        "type": "rss"
    },
    {
        "name": "国家统计局",
        "url": "http://www.stats.gov.cn/tjsj/tjgb/",
        "credibility": "高",
        "category": "中国宏观",
        "type": "html"
    }
]

def fetch_rss(url, source_name, credibility):
    """抓取 RSS 源"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        r = requests.get(url, timeout=10, headers=headers)
        if r.status_code != 200:
            return []
        
        # 简单解析 RSS
        items = []
        lines = r.text.split("\n")
        in_item = False
        item = {}
        
        for line in lines:
            if "<item>" in line:
                in_item = True
                item = {}
            elif "</item>" in line:
                in_item = False
                if item.get("title"):
                    items.append(item)
            elif in_item:
                if "<title>" in line and "</title>" in line:
                    title = line.split(">")[1].split("<")[0].strip()
                    item["title"] = title[:100]
                elif "<link>" in line and "</link>" in line:
                    link = line.split(">")[1].split("<")[0].strip()
                    item["link"] = link
                elif "<pubDate>" in line:
                    date = line.split(">")[1].split("<")[0].strip()
                    item["date"] = date[:30]
        
        news = []
        for i in items[:3]:
            news.append({
                "title": i.get("title", "无标题"),
                "source": source_name,
                "credibility": credibility,
                "link": i.get("link", ""),
                "date": i.get("date", ""),
                "summary": i.get("title", "")[:50]
            })
        return news
    except Exception as e:
        return []

def fetch_html_list(url, source_name, credibility, selectors=None):
    """抓取 HTML 列表页"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        r = requests.get(url, timeout=10, headers=headers)
        if r.status_code != 200:
            return []
        
        # 简单提取链接标题
        items = []
        import re
        # 匹配标题链接
        patterns = [
            r'<a[^>]*title="([^"]+)"[^>]*href="([^"]+)"',
            r'<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, r.text)
            for match in matches[:3]:
                if len(match) >= 2:
                    title = match[1] if len(match) > 1 else match[0]
                    link = match[0] if len(match) > 1 else match[1]
                    title = title.strip()
                    if title and len(title) > 5:
                        items.append({
                            "title": title[:100],
                            "source": source_name,
                            "credibility": credibility,
                            "link": urljoin(url, link),
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "summary": title[:50]
                        })
        
        return items[:3]
    except Exception as e:
        return []

def fetch_news():
    """抓取新闻"""
    # 先检查缓存
    cached = load_cache()
    if cached:
        return cached, "缓存模式"
    
    all_news = []
    
    for source in SOURCES:
        try:
            if source["type"] == "rss":
                news = fetch_rss(source["url"], source["name"], source["credibility"])
            else:
                news = fetch_html_list(source["url"], source["name"], source["credibility"])
            
            all_news.extend(news)
            time.sleep(1)  # 避免请求过快
        except:
            pass
    
    if all_news:
        save_cache(all_news)
        return all_news, "实时模式"
    
    return [], "无数据"

def format_output(news_list, mode):
    lines = []
    lines.append("="*50)
    lines.append("📰 新闻简报")
    lines.append("="*50)
    lines.append("")
    lines.append(f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"当前模式：{mode}")
    lines.append("")
    
    if not news_list:
        lines.append("当前无新增高可信新闻")
        lines.append("")
        lines.append("="*50)
        return "\n".join(lines)
    
    # 按可信度排序
    priority = {"高": 0, "中": 1, "低": 2}
    news_list.sort(key=lambda x: priority.get(x.get("credibility", "低"), 2))
    
    for i, item in enumerate(news_list[:5], 1):
        lines.append(f"--- {i}. {item.get('source', '未知')} ---")
        lines.append(f"标题：{item.get('title', '无')}")
        lines.append(f"可信度：{item.get('credibility', '低')}")
        lines.append(f"时间：{item.get('date', '')}")
        if item.get("link"):
            lines.append(f"链接：{item['link'][:60]}...")
        lines.append("")
    
    lines.append("="*50)
    return "\n".join(lines)

if __name__ == "__main__":
    news, mode = fetch_news()
    print(format_output(news, mode))
