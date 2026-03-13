#!/usr/bin/env python3
"""
Quant Analyst - 量化策略分析脚本
从 Binance Demo Trading API 获取真实数据
"""
import json
import os
import time
import hmac
import hashlib
import requests
from datetime import datetime
from dotenv import load_dotenv

# 加载 .env
load_dotenv("/Users/mac/.openclaw/workspace/openclaw-project/runs/grid_bot/.env")

# 配置
STATE_FILE = "/Users/mac/.openclaw/workspace/openclaw-project/runs/grid_bot/state_v2.json"
DEMO_API_BASE = "https://demo-api.binance.com"
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
SYMBOL = "BTCUSDT"


def load_state():
    """加载本地状态"""
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {}


def _demo_sign(query: str) -> str:
    """Demo API 签名"""
    return hmac.new(BINANCE_API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()


def _demo_request(method: str, endpoint: str, params: dict = None) -> dict:
    """Demo API 请求"""
    headers = {"X-MBX-APIKEY": BINANCE_API_KEY}
    
    ts = int(time.time() * 1000)
    if params:
        query = "&".join([f"{k}={v}" for k, v in params.items()])
        query += f"&timestamp={ts}&recvWindow=10000"
    else:
        query = f"timestamp={ts}&recvWindow=10000"
    
    signature = _demo_sign(query)
    url = f"{DEMO_API_BASE}{endpoint}?{query}&signature={signature}"
    
    if method == "GET":
        resp = requests.get(url, headers=headers)
    elif method == "POST":
        resp = requests.post(url, headers=headers)
    elif method == "DELETE":
        resp = requests.delete(url, headers=headers)
    else:
        raise ValueError(f"Unsupported method: {method}")
    
    if resp.status_code >= 400:
        raise Exception(f"Demo API error: {resp.status_code} {resp.text}")
    
    return resp.json()


# Demo API 连接状态
_demo_api_status = {"connected": True, "error": None}


def check_demo_api():
    """检查 Demo API 是否可用"""
    global _demo_api_status
    try:
        # 尝试调用实际接口来验证
        balance = _demo_request("GET", "/api/v3/account")
        _demo_api_status = {"connected": True, "error": None}
        return True
    except Exception as e:
        error_msg = str(e)
        if "502" in error_msg or "Bad Gateway" in error_msg:
            _demo_api_status = {"connected": False, "error": "502 Bad Gateway"}
        else:
            _demo_api_status = {"connected": False, "error": error_msg[:50]}
        return False


def get_demo_balance():
    """获取 Demo 账户真实余额"""
    if not _demo_api_status["connected"]:
        return {'USDT': None, 'USDC': None, 'BTC': None}
    
    try:
        result = _demo_request("GET", "/api/v3/account")
        balances = {b['asset']: {'free': float(b['free']), 'locked': float(b['locked'])} 
                    for b in result.get('balances', [])}
        
        return {
            'USDT': balances.get('USDT', {'free': 0})['free'],
            'USDC': balances.get('USDC', {'free': 0})['free'],
            'BTC': balances.get('BTC', {'free': 0})['free'],
        }
    except Exception as e:
        print(f"获取余额失败: {e}")
        return {'USDT': None, 'USDC': None, 'BTC': None}


def get_demo_price():
    """获取 BTC 当前价格"""
    if not _demo_api_status["connected"]:
        return None
    
    try:
        resp = requests.get(f"{DEMO_API_BASE}/api/v3/ticker/price?symbol=BTCUSDT")
        return float(resp.json()['price'])
    except Exception as e:
        print(f"获取价格失败: {e}")
        return None


def get_demo_open_orders():
    """获取 Demo 账户真实挂单"""
    if not _demo_api_status["connected"]:
        return []
    
    try:
        params = {"symbol": SYMBOL}
        result = _demo_request("GET", "/api/v3/openOrders", params)
        
        orders = []
        for o in result:
            if o.get('side') == 'BUY' and o.get('status') == 'NEW':
                orders.append({
                    'orderId': o.get('orderId'),
                    'price': float(o.get('price', 0)),
                    'origQty': float(o.get('origQty', 0)),
                    'executedQty': float(o.get('executedQty', 0)),
                    'price': float(o.get('price', 0)),
                    'symbol': o.get('symbol'),
                })
        return orders
    except Exception as e:
        print(f"获取挂单失败: {e}")
        return []


def analyze():
    # 先检查 Demo API 是否可用
    check_demo_api()
    
    # 尝试从 Demo API 获取数据
    try:
        balance = get_demo_balance()
        price = get_demo_price()
        orders = get_demo_open_orders()
        
        # 检查数据是否有效 - 先获取余额再检查
        quote_balance = balance.get('USDT') or balance.get('USDC') if balance else None
        
        if price is None or quote_balance is None:
            # Demo API 异常
            raise Exception(f"Demo API 异常: {_demo_api_status.get('error', '未知')}")
        
        # 使用 Demo 数据
        base_balance = balance.get('BTC', 0)
        
        # 策略参数
        total_u = quote_balance  # 使用账户实际余额作为总U
        
        # 计算挂单占用
        order_value = sum(o.get('origQty', 0) * o.get('price', 0) for o in orders)
        
        # 持仓占用 (如果有 BTC)
        position_value = base_balance * price if base_balance else 0
        
        used_u = position_value + order_value
        remaining_u = total_u - used_u
        utilization = (used_u / total_u * 100) if total_u > 0 else 0
        
        # 挂单价格
        order_prices = [o.get('price', 0) for o in orders if o.get('price', 0) > 0]
        order_prices.sort(reverse=True)
        
        current_layers = len(orders)
        max_layers = 6
        
        data_source = "Binance Demo Trading (真实)"
        
    except Exception as e:
        # Demo API 异常，返回 null 数据
        print(f"Demo API 异常: {e}")
        price = None
        quote_balance = None
        base_balance = None
        orders = []
        total_u = None
        order_value = 0
        position_value = 0
        used_u = 0
        remaining_u = None
        utilization = None
        order_prices = []
        current_layers = 0
        max_layers = 6
        data_source = f"Demo API 异常 ({_demo_api_status.get('error', '未知')})"
    
    # 风控判断
    risks = []
    actions = []
    
    # 只有在数据有效时才进行风控判断
    if utilization is not None:
        if current_layers >= max_layers:
            status = "critical"
            status_cn = "危险"
            conclusion = f"库存层数已到 {current_layers}/{max_layers}，已打满"
            risks.append(f"库存层数{current_layers}已打满")
            actions.append("暂停新开仓")
        elif current_layers >= 4:
            status = "warning"
            status_cn = "预警"
            conclusion = f"库存层数已到 {current_layers}/{max_layers}，接近上限"
            risks.append(f"库存层数{current_layers}接近上限{max_layers}")
            actions.append("关注加仓节奏")
        else:
            status = "ok"
            status_cn = "正常"
            conclusion = "库存层数适中，策略正常运行"
        
        if utilization > 85:
            status = "critical"
            conclusion = f"资金利用率{utilization:.1f}%超限"
            risks.append(f"资金利用率{utilization:.1f}%超限")
            actions.append("降低仓位")
    else:
        # 数据无效
        status = "failed"
        conclusion = "Demo API 异常，无法获取数据"
        risks.append("Demo API 异常")
        actions.append("检查 Demo API 连接")
    
    # 生成 JSON 输出
    output = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "data_source": data_source,
        "symbol": "BTC",
        "price_usd": price,
        "position_btc": base_balance,
        "inventory_layers_used": current_layers,
        "inventory_layers_limit": max_layers,
        "total_u": total_u,
        "used_u": round(used_u, 2) if used_u is not None else None,
        "open_orders_reserved_u": round(order_value, 2) if order_value is not None else None,
        "total_used_u": round(used_u, 2) if used_u is not None else None,
        "remaining_u": round(remaining_u, 2) if remaining_u is not None else None,
        "capital_utilization_pct": round(utilization, 1) if utilization is not None else None,
        "open_orders_count": len(orders) if orders is not None else None,
        "open_orders_prices": order_prices,
        "status": status,
        "risk_reason": "; ".join(risks) if risks else "暂无",
        "top_action": actions[0] if actions else "继续观察"
    }
    
    return output


def main():
    import sys
    
    result = analyze()
    
    # 只输出 JSON 到 stdout，错误信息到 stderr
    print(json.dumps(result, indent=2, ensure_ascii=False), file=sys.stdout)
    
    # 保存到文件
    output_file = "/Users/mac/.openclaw/workspace/openclaw-project/data/latest/quant_report.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
