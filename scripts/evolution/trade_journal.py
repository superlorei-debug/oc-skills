#!/usr/bin/env python3
"""
Trade Journal - 交易学习日志
记录结构化交易数据，用于后续策略评估

输出: data/evolution/trade_journal.json
"""
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/Users/mac/.openclaw/workspace/openclaw-project/runs/grid_bot/.env')

DATA_DIR = "/Users/mac/.openclaw/workspace/openclaw-project/data"
LATEST_DIR = f"{DATA_DIR}/latest"
EVOLUTION_DIR = f"{DATA_DIR}/evolution"

def load_latest_data():
    """加载最新状态数据"""
    data = {}
    
    # commander_status
    try:
        with open(f"{LATEST_DIR}/commander_status.json") as f:
            data['commander'] = json.load(f)
    except:
        pass
    
    # quant_report
    try:
        with open(f"{LATEST_DIR}/quant_report.json") as f:
            data['quant'] = json.load(f)
    except:
        pass
    
    # news
    try:
        with open(f"{LATEST_DIR}/news_report.json") as f:
            data['news'] = json.load(f)
    except:
        pass
    
    # macro
    try:
        with open(f"{LATEST_DIR}/macro_report.json") as f:
            data['macro'] = json.load(f)
    except:
        pass
    
    return data

def record_trade_event(event_type, order_data=None):
    """记录交易事件"""
    data = load_latest_data()
    
    # 加载现有日志
    journal_file = f"{EVOLUTION_DIR}/trade_journal.json"
    try:
        with open(journal_file) as f:
            journal = json.load(f)
    except:
        journal = {"events": [], "last_updated": None}
    
    # 构建事件记录
    event = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
    }
    
    # 添加订单数据
    if order_data:
        event.update(order_data)
    
    # 添加上下文数据
    if data.get('quant'):
        q = data['quant']
        event["context"] = {
            "btc_price": q.get("price_usdt"),
            "usdt_balance": q.get("total_u"),
            "position_btc": q.get("position_btc"),
            "inventory_layers_used": q.get("inventory_layers_used"),
            "utilization_pct": q.get("capital_utilization_pct"),
            "open_orders_count": q.get("open_orders_count"),
            "status": q.get("status"),
        }
    
    if data.get('commander'):
        c = data['commander']
        runtime = c.get("runtime", {})
        system = c.get("system", {})
        quant = c.get("quant", {})
        
        event["context"]["runtime"] = {
            "target_mode": runtime.get("target_mode"),
            "actual_mode": runtime.get("actual_mode"),
            "can_trade": quant.get("data_validity"),
        }
        event["context"]["system"] = {
            "bot_running": system.get("bot", {}).get("running"),
            "demo_api_connected": system.get("demo_api", {}).get("connected"),
        }
    
    # 添加到日志
    journal["events"].append(event)
    journal["last_updated"] = datetime.now().isoformat()
    
    # 只保留最近 1000 条
    if len(journal["events"]) > 1000:
        journal["events"] = journal["events"][-1000:]
    
    # 保存
    with open(journal_file, 'w') as f:
        json.dump(journal, f, indent=2, ensure_ascii=False)
    
    return event

def generate_summary():
    """生成交易摘要"""
    journal_file = f"{EVOLUTION_DIR}/trade_journal.json"
    try:
        with open(journal_file) as f:
            journal = json.load(f)
    except:
        return None
    
    events = journal.get("events", [])
    
    # 统计
    summary = {
        "total_events": len(events),
        "by_type": {},
        "last_24h": 0,
        "last_7d": 0,
    }
    
    now = datetime.now()
    from datetime import timedelta
    
    for event in events:
        et = event.get("event_type", "unknown")
        summary["by_type"][et] = summary["by_type"].get(et, 0) + 1
        
        # 时间计算
        try:
            event_time = datetime.fromisoformat(event["timestamp"])
            age = now - event_time
            
            if age < timedelta(days=1):
                summary["last_24h"] += 1
            if age < timedelta(days=7):
                summary["last_7d"] += 1
        except:
            pass
    
    return summary

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--record":
            # 记录事件
            event_type = sys.argv[2] if len(sys.argv) > 2 else "manual"
            order_data = None
            if len(sys.argv) > 3:
                try:
                    order_data = json.loads(sys.argv[3])
                except:
                    pass
            record_trade_event(event_type, order_data)
            print(f"✅ 记录事件: {event_type}")
        
        elif sys.argv[1] == "--summary":
            # 输出摘要
            summary = generate_summary()
            if summary:
                print(json.dumps(summary, indent=2, ensure_ascii=False))
            else:
                print("暂无交易日志")
    else:
        # 默认生成摘要
        summary = generate_summary()
        if summary:
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        else:
            print("暂无交易日志")
