#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced spot grid bot with Demo API Manager
- 工程化容错处理
- 三条链分离 (market/account/order)
- 熔断机制
- 恢复对账
"""

from __future__ import annotations

import itertools
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import ccxt
import requests
from dotenv import load_dotenv

# 导入 Demo API Manager
sys.path.insert(0, "/Users/mac/.openclaw/workspace/openclaw-project/scripts")
from demo_api_manager import DemoAPIManager, init_demo_api_manager, get_demo_api_manager

load_dotenv()

# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------
SYMBOL = os.getenv("SYMBOL", "BTC/USDT")
STATE_FILE = Path(__file__).resolve().parent / "state_v2.json"
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "10"))
PRICE_HISTORY_SIZE = int(os.getenv("PRICE_HISTORY_SIZE", "220"))
ESTIMATED_FEE_RATE = float(os.getenv("ESTIMATED_FEE_RATE", "0.001"))
SPREAD_MAX = float(os.getenv("SPREAD_MAX", "0.0018"))

# Paper portfolio
PAPER_START_QUOTE = float(os.getenv("PAPER_START_QUOTE", "5000"))
PAPER_START_BASE = float(os.getenv("PAPER_START_BASE", "0"))

# Grid logic
GRID_LEVELS = int(os.getenv("GRID_LEVELS", "6"))
GRID_STEP_BASE = float(os.getenv("GRID_STEP_BASE", "0.012"))
GRID_STEP_VOL_MULT = float(os.getenv("GRID_STEP_VOL_MULT", "0.35"))
GRID_STEP_MIN = float(os.getenv("GRID_STEP_MIN", "0.010"))
GRID_STEP_MAX = float(os.getenv("GRID_STEP_MAX", "0.030"))
GRID_TAKE_PROFIT_PCT = float(os.getenv("GRID_TAKE_PROFIT_PCT", "0.018"))
GRID_TOTAL_BUDGET_PCT = float(os.getenv("GRID_TOTAL_BUDGET_PCT", "0.35"))
GRID_LAYER_WEIGHTS = [0.65, 0.80, 1.00, 1.15, 1.35, 1.60]
MAX_NEW_BUYS_PER_TICK = int(os.getenv("MAX_NEW_BUYS_PER_TICK", "3"))

# Trend / breakout / crash handling
TREND_SHORT_WINDOW = int(os.getenv("TREND_SHORT_WINDOW", "18"))
TREND_LONG_WINDOW = int(os.getenv("TREND_LONG_WINDOW", "72"))
UPTREND_THRESHOLD = float(os.getenv("UPTREND_THRESHOLD", "0.0035"))
DOWNTREND_THRESHOLD = float(os.getenv("DOWNTREND_THRESHOLD", "-0.0035"))

BREAKOUT_LOOKBACK = int(os.getenv("BREAKOUT_LOOKBACK", "36"))
BREAKOUT_CONFIRM_PCT = float(os.getenv("BREAKOUT_CONFIRM_PCT", "0.003"))
BREAKOUT_TARGET_PCT = float(os.getenv("BREAKOUT_TARGET_PCT", "0.12"))
BREAKOUT_TRAIL_STOP_PCT = float(os.getenv("BREAKOUT_TRAIL_STOP_PCT", "0.015"))
BREAKOUT_COOLDOWN_SECONDS = int(os.getenv("BREAKOUT_COOLDOWN_SECONDS", str(30 * 60)))
BREAKOUT_ALLOC_PCT = float(os.getenv("BREAKOUT_ALLOC_PCT", "0.10"))

CORE_TARGET_PCT = float(os.getenv("CORE_TARGET_PCT", "0.20"))
CORE_REBALANCE_SECONDS = int(os.getenv("CORE_REBALANCE_SECONDS", str(30 * 60)))

CRASH_SHORT_LOOKBACK = int(os.getenv("CRASH_SHORT_LOOKBACK", "30"))
CRASH_LONG_LOOKBACK = int(os.getenv("CRASH_LONG_LOOKBACK", "90"))
CRASH_SHORT_DROP_PCT = float(os.getenv("CRASH_SHORT_DROP_PCT", "0.02"))
CRASH_LONG_DROP_PCT = float(os.getenv("CRASH_LONG_DROP_PCT", "0.04"))
CRASH_PAUSE_SECONDS = int(os.getenv("CRASH_PAUSE_SECONDS", str(60 * 60)))
CRASH_DELEVER_GRID_PCT = float(os.getenv("CRASH_DELEVER_GRID_PCT", "0.50"))

# Risk limits
MIN_CASH_RESERVE_PCT = float(os.getenv("MIN_CASH_RESERVE_PCT", "0.25"))
MAX_EXPOSURE_PCT = float(os.getenv("MAX_EXPOSURE_PCT", "0.70"))
SOFT_GRID_STOP_PCT = float(os.getenv("SOFT_GRID_STOP_PCT", "0.06"))
CIRCUIT_BREAKER_DROP_PCT = float(os.getenv("CIRCUIT_BREAKER_DROP_PCT", "0.05"))
DAILY_LOSS_LIMIT_PCT = float(os.getenv("DAILY_LOSS_LIMIT_PCT", "0.03"))

# Optional Telegram
TELEGRAM_TRADES_ONLY = os.getenv("TELEGRAM_TRADES_ONLY", "true").lower() == "true"
HEARTBEAT_TELEGRAM_SECONDS = int(os.getenv("HEARTBEAT_TELEGRAM_SECONDS", str(30 * 60)))

# -----------------------------------------------------------------------------
# Logging / telegram
# -----------------------------------------------------------------------------
def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] {msg}")


def telegram_send(msg: str) -> None:
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg},
            timeout=10,
        )
    except Exception as exc:
        log(f"telegram send failed: {exc}")


def t_send(msg: str, kind: str = "OTHER") -> None:
    if TELEGRAM_TRADES_ONLY and kind not in {"BUY_FILL", "SELL_FILL", "BAL_CHANGE"}:
        return
    telegram_send(msg)


# -----------------------------------------------------------------------------
# Exchange / market data
# -----------------------------------------------------------------------------
EXECUTION_MODE = os.getenv("EXECUTION_MODE", "paper")  # paper / binance_testnet / binance_demo / binance_live
BINANCE_TESTNET = os.getenv("BINANCE_TESTNET", "false").lower() == "true"

# 全局变量存储实际使用的模式
_actual_mode = EXECUTION_MODE

# Demo API 配置
DEMO_API_BASE = "https://demo-api.binance.com"
_demo_api_key = ""
_demo_api_secret = ""
_demo_api_manager = None  # DemoAPIManager 实例


def _demo_sign(query: str) -> str:
    """Demo API 签名"""
    import hmac
    import hashlib
    return hmac.new(_demo_api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()


def _demo_request(method: str, endpoint: str, params: dict = None) -> dict:
    """Demo API 请求"""
    import requests
    import time
    
    headers = {"X-MBX-APIKEY": _demo_api_key}
    
    # 构建查询字符串
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


def create_exchange() -> ccxt.Exchange:
    global _actual_mode, _demo_api_key, _demo_api_secret
    
    mode = EXECUTION_MODE
    api_key = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")
    
    if mode == "binance_demo":
        # 使用 Demo API Manager 进行工程化容错处理
        global _demo_api_manager
        
        # 初始化管理器
        _demo_api_manager = init_demo_api_manager(api_key, api_secret)
        
        # 启动前健康检查
        health = _demo_api_manager.health_check()
        
        if health["passed"]:
            _actual_mode = "binance_demo"
            log(f"✅ binance_demo 健康检查通过")
            log(f"   - ping: {health['checks'][0]['status']}")
            log(f"   - 账户读取: {health['checks'][1]['status']}")
            log(f"   - 订单读取: {health['checks'][2]['status']}")
        else:
            _actual_mode = "paper"
            _demo_api_manager.state.actual_mode = "paper"
            _demo_api_manager.state.degrade_reason = "健康检查失败"
            log(f"❌ binance_demo 健康检查失败，降级到 paper 模式")
            for check in health["checks"]:
                if check["status"] == "fail":
                    log(f"   - {check['name']}: {check.get('error', 'failed')}")
        
        # 返回 mock exchange 用于价格查询
        exchange = ccxt.binance({
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        })
        return exchange
    
    elif mode == "binance_testnet":
        # Testnet 模式 (备用)
        try:
            exchange = ccxt.binance({
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
                "options": {"defaultType": "spot"},
                "urls": {
                    "api": "https://testnet.binance.vision/api",
                },
            })
            exchange.fetch_ticker(SYMBOL)
            _actual_mode = "binance_testnet"
            log(f"Using binance_testnet mode")
            return exchange
        except Exception as e:
            log(f"testnet unavailable: {e}, fallback to paper mode")
            _actual_mode = "paper"
    
    elif mode == "binance_live":
        # 实盘
        if not api_key or not api_secret:
            log("BINANCE_API_KEY or SECRET not found, fallback to paper mode")
            _actual_mode = "paper"
        else:
            exchange = ccxt.binance({
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
                "options": {"defaultType": "spot"},
            })
            _actual_mode = "binance_live"
            log(f"Using binance_live mode")
            return exchange
    
    # 默认 paper 模式
    _actual_mode = "paper"
    return ccxt.binance({
        "enableRateLimit": True,
        "options": {"defaultType": "spot"},
    })


def is_testnet_mode() -> bool:
    """检查是否使用 testnet 模式"""
    return _actual_mode == "binance_testnet"


def is_live_mode() -> bool:
    """检查是否使用实盘模式"""
    return _actual_mode == "binance_live"


def is_paper_mode() -> bool:
    """检查是否使用 paper 模式"""
    return _actual_mode == "paper"


def with_retry(func, *args, **kwargs):
    delay = 2
    for attempt in range(10):
        try:
            return func(*args, **kwargs)
        except (ccxt.NetworkError, ccxt.RequestTimeout, ccxt.ExchangeError) as exc:
            if attempt == 9:
                raise
            log(f"retryable error: {exc}; sleeping {delay}s")
            time.sleep(delay)
            delay = min(delay * 2, 30)


def get_market(exchange: ccxt.Exchange) -> dict:
    markets = with_retry(exchange.load_markets)
    return markets[SYMBOL]


def get_last_price(exchange: ccxt.Exchange) -> float:
    ticker = with_retry(exchange.fetch_ticker, SYMBOL)
    return float(ticker["last"])


def get_order_book(exchange: ccxt.Exchange, limit: int = 5) -> dict:
    return with_retry(exchange.fetch_order_book, SYMBOL, limit)


def get_step_and_min_notional(market: dict) -> Tuple[Optional[str], Optional[float]]:
    step = None
    min_notional = None
    info = market.get("info", {}) or {}
    for f in info.get("filters", []):
        if f.get("filterType") == "LOT_SIZE":
            step = f.get("stepSize")
        if f.get("filterType") in {"MIN_NOTIONAL", "NOTIONAL"}:
            if f.get("minNotional") is not None:
                min_notional = float(f["minNotional"])
    if step is None:
        step = market.get("precision", {}).get("amount")
    return step, min_notional


def get_spread(exchange: ccxt.Exchange) -> Optional[float]:
    ob = get_order_book(exchange)
    bids = ob.get("bids") or []
    asks = ob.get("asks") or []
    if not bids or not asks:
        return None
    bid = float(bids[0][0])
    ask = float(asks[0][0])
    if bid <= 0:
        return None
    return (ask - bid) / bid


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def round_amount(amount: float, step: Optional[str]) -> float:
    if amount <= 0:
        return 0.0
    if step is None:
        return amount
    step_dec = Decimal(str(step))
    return float((Decimal(str(amount)) // step_dec) * step_dec)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_quote_code() -> str:
    return SYMBOL.split("/")[1]


def get_base_code() -> str:
    return SYMBOL.split("/")[0]


ID_COUNTER = itertools.count()


def new_id(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}_{next(ID_COUNTER)}"


def sma(values: List[float], window: int) -> Optional[float]:
    if len(values) < window or window <= 0:
        return None
    subset = values[-window:]
    return sum(subset) / len(subset)


def compute_volatility(price_history: List[float], window: int = 30) -> float:
    if len(price_history) < 2:
        return 0.0
    sample = price_history[-window:] if len(price_history) >= window else price_history
    min_p = min(sample)
    max_p = max(sample)
    if min_p <= 0:
        return 0.0
    return (max_p - min_p) / min_p


def adaptive_grid_step(volatility: float) -> float:
    step = GRID_STEP_BASE + volatility * GRID_STEP_VOL_MULT
    return max(GRID_STEP_MIN, min(GRID_STEP_MAX, step))


def weighted_avg_entry(positions: List[dict], strategy: Optional[str] = None) -> Optional[float]:
    selected = [p for p in positions if strategy is None or p["strategy"] == strategy]
    if not selected:
        return None
    total = sum(p["amount"] for p in selected)
    if total <= 0:
        return None
    return sum(p["amount"] * p["entry_price"] for p in selected) / total


def total_amount(positions: List[dict], strategy: Optional[str] = None) -> float:
    return sum(p["amount"] for p in positions if strategy is None or p["strategy"] == strategy)


# -----------------------------------------------------------------------------
# State / paper portfolio
# -----------------------------------------------------------------------------
def default_state() -> dict:
    return {
        "anchor_price": None,
        "open_buy_orders": [],
        "positions": [],
        "realized_pnl_quote": 0.0,
        "fees_paid_quote": 0.0,
        "equity_peak": None,
        "pause_until_ts": None,
        "crash_mode_until_ts": None,
        "today_start_equity": None,
        "today_pnl_quote": 0.0,
        "last_action_ts": None,
        "bot_start_ts": time.time(),
        "last_equity_quote": None,
        "paper_quote_balance": PAPER_START_QUOTE,
        "paper_base_balance": PAPER_START_BASE,
        "paper_reserved_quote": 0.0,
        "last_regime": None,
        "last_regime_reason": None,
        "last_core_rebalance_ts": None,
        "last_breakout_entry_ts": None,
        "last_heartbeat_ts": 0.0,
        "_last_day": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


def load_state() -> dict:
    state = default_state()
    if not STATE_FILE.exists():
        return state
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        state.update(data)
        return state
    except Exception as exc:
        log(f"state load error: {exc}; starting with defaults")
        return state


def save_state(state: dict) -> None:
    state["last_action_ts"] = now_iso()
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def paper_total_quote_balance(state: dict) -> float:
    return float(state.get("paper_quote_balance", 0.0))


def paper_total_base_balance(state: dict) -> float:
    return float(state.get("paper_base_balance", 0.0))


def paper_reserved_quote(state: dict) -> float:
    return float(state.get("paper_reserved_quote", 0.0))


def paper_free_quote(state: dict) -> float:
    return max(0.0, paper_total_quote_balance(state) - paper_reserved_quote(state))


def paper_equity_quote(state: dict, last_price: float) -> float:
    return paper_total_quote_balance(state) + paper_total_base_balance(state) * last_price


def exposure_pct(state: dict, last_price: float) -> float:
    eq = paper_equity_quote(state, last_price)
    if eq <= 0:
        return 0.0
    return (paper_total_base_balance(state) * last_price) / eq


def cash_reserve_pct(state: dict, last_price: float) -> float:
    eq = paper_equity_quote(state, last_price)
    if eq <= 0:
        return 1.0
    return paper_free_quote(state) / eq


def is_paused(state: dict) -> bool:
    ts = state.get("pause_until_ts")
    return bool(ts and time.time() < ts)


def in_crash_mode(state: dict) -> bool:
    ts = state.get("crash_mode_until_ts")
    return bool(ts and time.time() < ts)


# -----------------------------------------------------------------------------
# Regime detection
# -----------------------------------------------------------------------------
def detect_market_regime(price_history: List[float], spread: Optional[float]) -> Tuple[str, str, Dict[str, float]]:
    if len(price_history) < max(TREND_LONG_WINDOW, CRASH_LONG_LOOKBACK) + 2:
        return "RANGE", "warming_up", {}

    last_price = price_history[-1]
    short_ma = sma(price_history, TREND_SHORT_WINDOW)
    long_ma = sma(price_history, TREND_LONG_WINDOW)
    short_ret = last_price / price_history[-CRASH_SHORT_LOOKBACK] - 1.0
    long_ret = last_price / price_history[-CRASH_LONG_LOOKBACK] - 1.0
    trend_strength = 0.0 if not short_ma or not long_ma or long_ma <= 0 else short_ma / long_ma - 1.0

    metrics = {
        "short_ma": short_ma or 0.0,
        "long_ma": long_ma or 0.0,
        "short_ret": short_ret,
        "long_ret": long_ret,
        "trend_strength": trend_strength,
    }

    if spread is not None and spread > SPREAD_MAX * 2.0:
        return "CRASH", "spread_spike", metrics
    if short_ret <= -CRASH_SHORT_DROP_PCT:
        return "CRASH", f"{CRASH_SHORT_LOOKBACK}_tick_drop", metrics
    if long_ret <= -CRASH_LONG_DROP_PCT:
        return "CRASH", f"{CRASH_LONG_LOOKBACK}_tick_drop", metrics

    if short_ma and long_ma:
        if trend_strength >= UPTREND_THRESHOLD and last_price > long_ma:
            return "UPTREND", "ma_alignment_up", metrics
        if trend_strength <= DOWNTREND_THRESHOLD and last_price < long_ma:
            return "DOWNTREND", "ma_alignment_down", metrics

    return "RANGE", "neutral", metrics


# -----------------------------------------------------------------------------
# Position / PnL accounting
# -----------------------------------------------------------------------------
def add_position(state: dict, strategy: str, amount: float, entry_price: float, **extra) -> str:
    position_id = new_id(f"pos_{strategy}")
    position = {
        "position_id": position_id,
        "strategy": strategy,
        "amount": amount,
        "entry_price": entry_price,
        "opened_ts": time.time(),
    }
    position.update(extra)
    state["positions"].append(position)
    return position_id


def book_fee(state: dict, fee_quote: float) -> None:
    state["fees_paid_quote"] = state.get("fees_paid_quote", 0.0) + fee_quote


def paper_market_buy(state: dict, last_price: float, quote_notional: float, strategy: str, note: str = "") -> Optional[str]:
    if quote_notional <= 0:
        return None
    fee = quote_notional * ESTIMATED_FEE_RATE
    total_cost = quote_notional + fee
    if paper_free_quote(state) < total_cost:
        return None
    amount = quote_notional / last_price
    state["paper_quote_balance"] -= total_cost
    state["paper_base_balance"] += amount
    book_fee(state, fee)
    position_id = add_position(state, strategy, amount, last_price, note=note, highest_price=last_price)
    log(f"PAPER BUY strategy={strategy} quote≈{quote_notional:.2f} amount≈{amount:.6f} price≈{last_price:.2f} {note}")
    t_send(f"BUY {strategy}: quote≈{quote_notional:.2f} price≈{last_price:.2f}", "BUY_FILL")
    return position_id


def sell_one_position(state: dict, position: dict, amount_to_sell: float, sell_price: float, reason: str = "") -> float:
    amount_to_sell = min(amount_to_sell, position["amount"], paper_total_base_balance(state))
    if amount_to_sell <= 0:
        return 0.0

    gross_quote = amount_to_sell * sell_price
    fee = gross_quote * ESTIMATED_FEE_RATE
    pnl = (sell_price - position["entry_price"]) * amount_to_sell - fee

    state["paper_base_balance"] -= amount_to_sell
    state["paper_quote_balance"] += gross_quote - fee
    state["realized_pnl_quote"] = state.get("realized_pnl_quote", 0.0) + pnl
    book_fee(state, fee)

    position["amount"] -= amount_to_sell
    if position["amount"] <= 1e-12:
        state["positions"] = [p for p in state.get("positions", []) if p["position_id"] != position["position_id"]]

    log(
        f"PAPER SELL strategy={position['strategy']} amount≈{amount_to_sell:.6f} "
        f"price≈{sell_price:.2f} pnl≈{pnl:.2f} {reason}"
    )
    t_send(f"SELL {position['strategy']}: amount≈{amount_to_sell:.6f} price≈{sell_price:.2f} pnl≈{pnl:.2f}", "SELL_FILL")
    return amount_to_sell


def paper_market_sell_positions(
    state: dict,
    last_price: float,
    sell_amount: float,
    strategies: Optional[List[str]] = None,
    reason: str = "",
) -> float:
    remaining = sell_amount
    sold_total = 0.0
    candidates = [
        p for p in sorted(state.get("positions", []), key=lambda x: x["opened_ts"])
        if strategies is None or p["strategy"] in strategies
    ]
    for p in candidates:
        if remaining <= 0:
            break
        sold = sell_one_position(state, p, min(remaining, p["amount"]), last_price, reason=reason)
        remaining -= sold
        sold_total += sold
    return sold_total


# -----------------------------------------------------------------------------
# Order simulation
# -----------------------------------------------------------------------------
def reserve_quote(state: dict, amount: float) -> bool:
    if amount <= 0:
        return False
    if paper_free_quote(state) < amount:
        return False
    state["paper_reserved_quote"] += amount
    return True


def release_quote(state: dict, amount: float) -> None:
    state["paper_reserved_quote"] = max(0.0, paper_reserved_quote(state) - max(0.0, amount))


# -----------------------------------------------------------------------------
# Exchange Order Functions (for testnet/live mode)
# -----------------------------------------------------------------------------
_exchange_instance = None

def get_exchange():
    """获取交易所实例（单例）"""
    global _exchange_instance
    if _exchange_instance is None:
        _exchange_instance = create_exchange()
    return _exchange_instance


def is_demo_mode() -> bool:
    """检查是否使用 demo 模式"""
    return _actual_mode == "binance_demo"


def exchange_place_buy(exchange, price: float, amount: float) -> Optional[dict]:
    """在交易所下单买入（使用 DemoAPIManager）"""
    try:
        # 检查是否可以交易
        if is_demo_mode() and _demo_api_manager:
            status = _demo_api_manager.get_status()
            if not status.get("can_trade"):
                log(f"EXCHANGE BUY SKIPPED: Demo API not available (mode={status['actual_mode']}, circuit_broken={status['circuit_broken']})")
                return None
            
            # 使用 Manager 下单
            result = _demo_api_manager.place_order(price, amount)
            if result:
                log(f"EXCHANGE BUY (demo): order_id={result.get('orderId')} price={price} amount={amount}")
            else:
                log(f"EXCHANGE BUY FAILED: Demo API order failed")
            return result
        else:
            # 标准 ccxt 模式
            order = exchange.create_order(
                symbol=SYMBOL,
                type="limit",
                side="buy",
                amount=amount,
                price=price,
            )
            log(f"EXCHANGE BUY: order_id={order.get('id')} price={price} amount={amount}")
            return order
    except Exception as e:
        log(f"EXCHANGE BUY FAILED: {e}")
        return None


def exchange_cancel_order(exchange, order_id: str) -> bool:
    """取消交易所订单（使用 DemoAPIManager）"""
    try:
        if is_demo_mode() and _demo_api_manager:
            result = _demo_api_manager.cancel_order(order_id)
            if result:
                log(f"EXCHANGE CANCEL (demo): {order_id}")
            else:
                log(f"EXCHANGE CANCEL FAILED: {order_id}")
            return result
        else:
            exchange.cancel_order(order_id, SYMBOL)
            log(f"EXCHANGE CANCEL: {order_id}")
            return True
    except Exception as e:
        log(f"EXCHANGE CANCEL FAILED: {e}")
        return False


def exchange_get_balance(exchange) -> dict:
    """获取交易所余额（使用 DemoAPIManager）"""
    try:
        if is_demo_mode() and _demo_api_manager:
            balance = _demo_api_manager.get_balance()
            if balance:
                # 确定 quote 货币
                quote = "USDT" if balance.get('USDT', 0) > 0 else "USDC"
                return {
                    "free_quote": balance.get(quote, 0),
                    "free_base": balance.get("BTC", 0),
                    "total_quote": balance.get(quote, 0),
                    "total_base": balance.get("BTC", 0),
                }
            # 获取失败返回 null
            return {"free_quote": None, "free_base": None, "total_quote": None, "total_base": None}
        else:
            balance = exchange.fetch_balance()
            return {
                "free_quote": float(balance.get("free", {}).get("USDC", 0)),
                "free_base": float(balance.get("free", {}).get("BTC", 0)),
                "total_quote": float(balance.get("total", {}).get("USDC", 0)),
                "total_base": float(balance.get("total", {}).get("BTC", 0)),
            }
    except Exception as e:
        log(f"EXCHANGE FETCH BALANCE FAILED: {e}")
        return {"free_quote": None, "free_base": None, "total_quote": None, "total_base": None}
        if is_demo_mode():
            # Demo 模式
            result = _demo_request("GET", "/api/v3/account")
            balances = {b['asset']: float(b['free']) for b in result.get('balances', [])}
            
            # 确定 quote 货币 (USDT 或 USDC)
            quote = "USDT" if "USDT" in balances else "USDC"
            
            return {
                "free_quote": balances.get(quote, 0),
                "free_base": balances.get("BTC", 0),
                "total_quote": balances.get(quote, 0),
                "total_base": balances.get("BTC", 0),
            }
        else:
            # 标准 ccxt 模式
            balance = exchange.fetch_balance()
            return {
                "free_quote": float(balance.get("free", {}).get("USDC", 0)),
                "free_base": float(balance.get("free", {}).get("BTC", 0)),
                "total_quote": float(balance.get("total", {}).get("USDC", 0)),
                "total_base": float(balance.get("total", {}).get("BTC", 0)),
            }
    except Exception as e:
        log(f"EXCHANGE FETCH BALANCE FAILED: {e}")
        return {"free_quote": 0, "free_base": 0, "total_quote": 0, "total_base": 0}


def sync_state_from_exchange(state: dict) -> None:
    """从交易所同步状态（testnet/live/demo模式）"""
    if is_paper_mode():
        return
    
    try:
        exchange = get_exchange()
        
        # 同步余额
        balance = exchange_get_balance(exchange)
        state["paper_quote_balance"] = balance["free_quote"]
        state["paper_base_balance"] = balance["free_base"]
        
        # 同步挂单
        open_orders = exchange_get_open_orders(exchange)
        
        # 确定 quote 货币
        quote = "USDT" if is_demo_mode() else "USDC"
        
        # 转换交易所订单格式为本地图格式
        exchange_orders = []
        for order in open_orders:
            if order.get("side") == "buy":
                exchange_orders.append({
                    "order_id": order.get("id"),
                    "exchange_order_id": order.get("id"),
                    "price": float(order.get("price", 0)),
                    "amount": float(order.get("amount", 0)),
                    "notional": float(order.get("amount", 0)) * float(order.get("price", 0)),
                    "created_ts": order.get("timestamp", time.time()) / 1000,
                    "status": order.get("status", "open"),
                })
        
        # 合并挂单（保留本地标记的信息）
        existing = {o.get("exchange_order_id"): o for o in state.get("open_buy_orders", []) if o.get("exchange_order_id")}
        for ex_order in exchange_orders:
            ex_id = ex_order.get("exchange_order_id")
            if ex_id in existing:
                # 合并信息
                local = existing[ex_id]
                ex_order["level"] = local.get("level")
                ex_order["take_profit_pct"] = local.get("take_profit_pct", GRID_TAKE_PROFIT_PCT)
        
        state["open_buy_orders"] = exchange_orders
        
        log(f"SYNC FROM EXCHANGE: balance={balance['free_quote']:.2f} {quote}, orders={len(exchange_orders)}")
    except Exception as e:
        log(f"SYNC FROM EXCHANGE FAILED: {e}")


def exchange_get_open_orders(exchange) -> list:
    """获取交易所开放订单"""
    try:
        if is_demo_mode():
            # Demo 模式
            symbol = SYMBOL.replace("/", "")
            params = {"symbol": symbol}
            result = _demo_request("GET", "/api/v3/openOrders", params)
            
            # 转换为 ccxt 格式
            orders = []
            for o in result:
                orders.append({
                    "id": str(o.get("orderId")),
                    "side": o.get("side", "").lower(),
                    "price": float(o.get("price", 0)),
                    "amount": float(o.get("origQty", 0)) - float(o.get("executedQty", 0)),
                    "symbol": o.get("symbol"),
                    "status": "open" if o.get("status") == "NEW" else o.get("status").lower(),
                    "timestamp": o.get("time", 0),
                })
            return orders
        else:
            # 标准 ccxt 模式
            orders = exchange.fetch_open_orders(SYMBOL)
            return orders
    except Exception as e:
        log(f"EXCHANGE FETCH OPEN ORDERS FAILED: {e}")
        return []


def place_grid_buy_order(
    state: dict,
    level: int,
    price: float,
    quote_notional: float,
    step: Optional[str],
    min_notional: Optional[float],
) -> bool:
    if quote_notional <= 0 or price <= 0:
        return False
    amount = quote_notional / price
    amount = round_amount(amount, step)
    if amount <= 0:
        return False
    notional = amount * price
    if min_notional is not None and notional < min_notional:
        return False
    
    # 根据模式选择
    if is_paper_mode():
        # Paper 模式 - 本地模拟
        fee_buffer = notional * ESTIMATED_FEE_RATE
        reserve_need = notional + fee_buffer
        if not reserve_quote(state, reserve_need):
            return False

        order = {
            "order_id": new_id("buy"),
            "level": level,
            "price": price,
            "amount": amount,
            "notional": notional,
            "reserved_quote": reserve_need,
            "created_ts": time.time(),
            "status": "open",
            "take_profit_pct": GRID_TAKE_PROFIT_PCT,
        }
        state["open_buy_orders"].append(order)
        log(f"PLACE BUY level={level} price≈{price:.2f} amount≈{amount:.6f} notional≈{notional:.2f}")
    else:
        # Testnet/Live 模式 - 真正下单
        exchange = get_exchange()
        order = exchange_place_buy(exchange, price, amount)
        if order:
            # 记录订单信息
            order_info = {
                "order_id": order.get("id"),
                "level": level,
                "price": price,
                "amount": amount,
                "notional": notional,
                "created_ts": time.time(),
                "status": "open",
                "take_profit_pct": GRID_TAKE_PROFIT_PCT,
                "exchange_order_id": order.get("id"),
            }
            state["open_buy_orders"].append(order_info)
            log(f"EXCHANGE PLACE BUY level={level} price≈{price:.2f} amount≈{amount:.6f} order_id={order.get('id')}")
        else:
            log(f"EXCHANGE PLACE BUY FAILED level={level}")
            return False
    
    return True


def cancel_all_buy_orders(state: dict, reason: str = "") -> None:
    orders = state.get("open_buy_orders", [])
    if not orders:
        return
    
    if is_paper_mode():
        # Paper 模式 - 本地释放
        released = sum(o.get("reserved_quote", 0.0) for o in orders)
        release_quote(state, released)
        state["open_buy_orders"] = []
        log(f"cancelled all buy orders count={len(orders)} released≈{released:.2f} reason={reason}")
    else:
        # Testnet/Live 模式 - 交易所撤单
        exchange = get_exchange()
        cancelled = 0
        for order in orders:
            ex_order_id = order.get("exchange_order_id") or order.get("order_id")
            if exchange_cancel_order(exchange, ex_order_id):
                cancelled += 1
        state["open_buy_orders"] = []
        log(f"EXCHANGE cancelled all buy orders count={cancelled}/{len(orders)} reason={reason}")


def cancel_buy_orders_by_levels(state: dict, levels: List[int], reason: str = "") -> None:
    if not levels:
        return
    keep_orders = []
    released = 0.0
    cancelled = 0
    level_set = set(levels)
    for order in state.get("open_buy_orders", []):
        if order.get("level") in level_set:
            released += order.get("reserved_quote", 0.0)
            cancelled += 1
        else:
            keep_orders.append(order)
    if cancelled:
        release_quote(state, released)
        state["open_buy_orders"] = keep_orders
        log(f"cancelled buy orders by levels={sorted(level_set)} count={cancelled} released≈{released:.2f} reason={reason}")


def simulate_grid_buy_fills(state: dict, last_price: float) -> None:
    remaining_orders = []
    for order in state.get("open_buy_orders", []):
        if last_price <= order["price"]:
            release_quote(state, order.get("reserved_quote", 0.0))
            position_id = paper_market_buy(state, order["price"], order["notional"], "grid", note=f"grid_level_{order['level']}")
            if position_id:
                for p in state["positions"]:
                    if p["position_id"] == position_id:
                        p["target_price"] = order["price"] * (1 + order.get("take_profit_pct", GRID_TAKE_PROFIT_PCT))
                        break
        else:
            remaining_orders.append(order)
    state["open_buy_orders"] = remaining_orders


def simulate_grid_take_profits(state: dict, last_price: float) -> None:
    grid_positions = [p for p in list(state.get("positions", [])) if p["strategy"] == "grid"]
    for p in grid_positions:
        target = p.get("target_price") or p["entry_price"] * (1 + GRID_TAKE_PROFIT_PCT)
        if last_price >= target:
            sold = sell_one_position(state, p, p["amount"], target, reason="grid_take_profit")
            if sold > 0:
                state["anchor_price"] = target


# -----------------------------------------------------------------------------
# Risk / daily accounting
# -----------------------------------------------------------------------------
def refresh_daily_stats(state: dict, equity_quote: float) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if state.get("_last_day") != today:
        state["_last_day"] = today
        state["today_start_equity"] = equity_quote
        state["today_pnl_quote"] = 0.0
    if state.get("today_start_equity") is None:
        state["today_start_equity"] = equity_quote
    state["today_pnl_quote"] = equity_quote - state["today_start_equity"]
    state["last_equity_quote"] = equity_quote
    peak = state.get("equity_peak")
    if peak is None or equity_quote > peak:
        state["equity_peak"] = equity_quote


def maybe_trigger_daily_loss_pause(state: dict) -> bool:
    start_eq = state.get("today_start_equity")
    if not start_eq or start_eq <= 0:
        return False
    today_pnl = state.get("today_pnl_quote", 0.0)
    if today_pnl / start_eq > -DAILY_LOSS_LIMIT_PCT:
        return False
    state["pause_until_ts"] = time.time() + 6 * 60 * 60
    cancel_all_buy_orders(state, reason="daily_loss_pause")
    log(f"daily loss pause triggered pnl={today_pnl:.2f}")
    return True


def maybe_trigger_circuit_breaker(state: dict, equity_quote: float) -> bool:
    peak = state.get("equity_peak")
    if not peak or peak <= 0:
        return False
    dd = equity_quote / peak - 1.0
    if dd > -CIRCUIT_BREAKER_DROP_PCT:
        return False
    state["pause_until_ts"] = time.time() + 6 * 60 * 60
    cancel_all_buy_orders(state, reason="circuit_breaker")
    log(f"circuit breaker triggered dd={dd:.2%}")
    return True


# -----------------------------------------------------------------------------
# Regime actions: core / breakout / crash / soft stop
# -----------------------------------------------------------------------------
def handle_crash_mode(state: dict, last_price: float) -> None:
    state["crash_mode_until_ts"] = time.time() + CRASH_PAUSE_SECONDS
    cancel_all_buy_orders(state, reason="crash_mode")

    breakout_amt = total_amount(state.get("positions", []), "breakout")
    if breakout_amt > 0:
        paper_market_sell_positions(state, last_price, breakout_amt, strategies=["breakout"], reason="crash_exit_breakout")

    grid_amt = total_amount(state.get("positions", []), "grid")
    if grid_amt > 0:
        sell_amt = grid_amt * CRASH_DELEVER_GRID_PCT
        paper_market_sell_positions(state, last_price, sell_amt, strategies=["grid"], reason="crash_delever_grid")


def manage_core_position(state: dict, regime: str, last_price: float, equity_quote: float) -> None:
    if regime not in {"UPTREND", "RANGE"}:
        return
    now_ts = time.time()
    if state.get("last_core_rebalance_ts") and now_ts - state["last_core_rebalance_ts"] < CORE_REBALANCE_SECONDS:
        return

    target_notional = equity_quote * CORE_TARGET_PCT
    core_amt = total_amount(state.get("positions", []), "core")
    current_notional = core_amt * last_price

    state["last_core_rebalance_ts"] = now_ts

    if target_notional <= 0:
        return

    if current_notional < target_notional * 0.75:
        buy_notional = min(target_notional - current_notional, paper_free_quote(state) * 0.80)
        if buy_notional > 10:
            paper_market_buy(state, last_price, buy_notional, "core", note="core_rebalance_buy")
    elif current_notional > target_notional * 1.35:
        sell_notional = current_notional - target_notional
        sell_amount = sell_notional / last_price
        if sell_amount > 0:
            paper_market_sell_positions(state, last_price, sell_amount, strategies=["core"], reason="core_rebalance_sell")


def breakout_entry_signal(price_history: List[float], last_price: float, regime: str) -> bool:
    if regime != "UPTREND" or len(price_history) < BREAKOUT_LOOKBACK + 2:
        return False
    highest_prev = max(price_history[-BREAKOUT_LOOKBACK - 1:-1])
    return last_price > highest_prev * (1 + BREAKOUT_CONFIRM_PCT)


def manage_breakout_position(state: dict, regime: str, price_history: List[float], last_price: float, equity_quote: float) -> None:
    breakout_positions = [p for p in state.get("positions", []) if p["strategy"] == "breakout"]

    for p in breakout_positions:
        p["highest_price"] = max(p.get("highest_price", p["entry_price"]), last_price)
        trail_stop = p["highest_price"] * (1 - BREAKOUT_TRAIL_STOP_PCT)
        hard_target = p["entry_price"] * (1 + BREAKOUT_TARGET_PCT)
        if last_price <= trail_stop:
            sell_one_position(state, p, p["amount"], last_price, reason="breakout_trailing_stop")
        elif last_price >= hard_target:
            sell_one_position(state, p, p["amount"], last_price, reason="breakout_target")
        elif regime == "DOWNTREND":
            sell_one_position(state, p, p["amount"], last_price, reason="breakout_exit_downtrend")

    cooldown_ok = not state.get("last_breakout_entry_ts") or (time.time() - state["last_breakout_entry_ts"]) >= BREAKOUT_COOLDOWN_SECONDS
    if not cooldown_ok:
        return
    if any(p["strategy"] == "breakout" for p in state.get("positions", [])):
        return
    if not breakout_entry_signal(price_history, last_price, regime):
        return

    notional = min(equity_quote * BREAKOUT_ALLOC_PCT, paper_free_quote(state) * 0.90)
    if notional <= 10:
        return
    position_id = paper_market_buy(state, last_price, notional, "breakout", note="breakout_entry")
    if position_id:
        state["last_breakout_entry_ts"] = time.time()


def maybe_soft_stop_grid(state: dict, regime: str, last_price: float) -> None:
    grid_amt = total_amount(state.get("positions", []), "grid")
    if grid_amt <= 0:
        return
    avg_grid = weighted_avg_entry(state.get("positions", []), "grid")
    if avg_grid is None:
        return
    if last_price > avg_grid * (1 - SOFT_GRID_STOP_PCT):
        return
    if regime not in {"DOWNTREND", "CRASH"}:
        return

    cancel_all_buy_orders(state, reason="soft_stop_grid")
    sold = paper_market_sell_positions(
        state,
        last_price,
        grid_amt * 0.50,
        strategies=["grid"],
        reason="soft_stop_grid",
    )
    if sold > 0:
        log(f"soft stop sold grid amount≈{sold:.6f}")


def grid_level_notional(equity_quote: float, level: int) -> float:
    weights = GRID_LAYER_WEIGHTS[:GRID_LEVELS]
    weight_sum = sum(weights)
    total_budget = equity_quote * GRID_TOTAL_BUDGET_PCT
    return total_budget * weights[level] / weight_sum


def place_range_grid_orders(
    state: dict,
    last_price: float,
    anchor: float,
    grid_step_pct: float,
    equity_quote: float,
    step: Optional[str],
    min_notional: Optional[float],
) -> None:
    if is_paused(state) or in_crash_mode(state):
        return
    if cash_reserve_pct(state, last_price) < MIN_CASH_RESERVE_PCT:
        return
    if exposure_pct(state, last_price) >= MAX_EXPOSURE_PCT:
        return

    budget_cap = equity_quote * GRID_TOTAL_BUDGET_PCT
    current_reserved = sum(o.get("reserved_quote", 0.0) for o in state.get("open_buy_orders", []))
    existing_by_level = {}
    stale_levels = []

    for order in state.get("open_buy_orders", []):
        level = order.get("level")
        desired_price = anchor * (1 - (level + 1) * grid_step_pct)
        # 同一层只保留一个挂单；偏离当前目标价太多的旧单先撤掉
        if level in existing_by_level:
            stale_levels.append(level)
            continue
        if desired_price > 0 and abs(order["price"] - desired_price) / desired_price > max(0.0025, grid_step_pct * 0.35):
            stale_levels.append(level)
            continue
        existing_by_level[level] = order

    if stale_levels:
        cancel_buy_orders_by_levels(state, stale_levels, reason="refresh_range_grid")
        current_reserved = sum(o.get("reserved_quote", 0.0) for o in state.get("open_buy_orders", []))
        existing_by_level = {o["level"]: o for o in state.get("open_buy_orders", [])}

    placed = 0
    for i in range(GRID_LEVELS):
        if placed >= MAX_NEW_BUYS_PER_TICK:
            break
        if i in existing_by_level:
            continue
        level_price = anchor * (1 - (i + 1) * grid_step_pct)
        if last_price <= level_price:
            continue

        budget_left = budget_cap - current_reserved
        if budget_left <= 0:
            break

        raw_notional = grid_level_notional(equity_quote, i)
        max_notional_by_budget = budget_left / (1 + ESTIMATED_FEE_RATE)
        notional = min(raw_notional, max_notional_by_budget)
        ok = place_grid_buy_order(state, i, level_price, notional, step, min_notional)
        if ok:
            placed += 1
            current_reserved += state["open_buy_orders"][-1]["reserved_quote"]


# -----------------------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------------------
def main() -> None:
    exchange = create_exchange()
    market = get_market(exchange)
    step, min_notional = get_step_and_min_notional(market)
    state = load_state()

    if state.get("anchor_price") is None:
        state["anchor_price"] = get_last_price(exchange)
        save_state(state)

    price_history: List[float] = []
    last_regime_logged = None

    def shutdown_handler(signum, frame):
        log(f"received signal={signum}; saving state")
        save_state(state)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    log(f"starting enhanced paper bot for {SYMBOL}")
    log(f"execution mode: {_actual_mode}")
    log(
        f"paper start balance: {paper_total_quote_balance(state):.2f} {get_quote_code()} + "
        f"{paper_total_base_balance(state):.6f} {get_base_code()}"
    )

    while True:
        try:
            # Testnet/Live 模式：从交易所同步状态
            if not is_paper_mode():
                sync_state_from_exchange(state)
            
            last_price = get_last_price(exchange)
            spread = get_spread(exchange)
            price_history.append(last_price)
            if len(price_history) > PRICE_HISTORY_SIZE:
                price_history.pop(0)

            volatility = compute_volatility(price_history)
            grid_step_pct = adaptive_grid_step(volatility)
            regime, regime_reason, metrics = detect_market_regime(price_history, spread)

            equity_quote = paper_equity_quote(state, last_price)
            refresh_daily_stats(state, equity_quote)
            free_quote = paper_free_quote(state)
            exp_pct = exposure_pct(state, last_price)
            cash_pct = cash_reserve_pct(state, last_price)

            if regime != state.get("last_regime"):
                state["last_regime"] = regime
                state["last_regime_reason"] = regime_reason
                save_state(state)

            if regime != last_regime_logged:
                metric_s = ", ".join(f"{k}={v:.5f}" for k, v in metrics.items()) if metrics else "warmup"
                log(f"REGIME => {regime} reason={regime_reason} metrics={{{metric_s}}}")
                last_regime_logged = regime

            if spread is not None and spread > SPREAD_MAX:
                log(f"spread guard active spread={spread:.5f}")

            if maybe_trigger_circuit_breaker(state, equity_quote):
                save_state(state)
                time.sleep(POLL_SECONDS)
                continue
            if maybe_trigger_daily_loss_pause(state):
                save_state(state)
                time.sleep(POLL_SECONDS)
                continue

            if regime == "CRASH" and not in_crash_mode(state):
                log(f"CRASH MODE ENTER reason={regime_reason}")
                t_send(f"CRASH MODE entered: {regime_reason}", "OTHER")
                handle_crash_mode(state, last_price)
                save_state(state)
                time.sleep(POLL_SECONDS)
                continue

            simulate_grid_buy_fills(state, last_price)
            simulate_grid_take_profits(state, last_price)
            maybe_soft_stop_grid(state, regime, last_price)
            manage_breakout_position(state, regime, price_history, last_price, equity_quote)
            manage_core_position(state, regime, last_price, equity_quote)

            if regime in {"DOWNTREND", "CRASH"}:
                cancel_all_buy_orders(state, reason=f"regime_{regime.lower()}")
            elif regime == "UPTREND":
                cancel_all_buy_orders(state, reason="uptrend_no_grid")
            else:
                anchor = state.get("anchor_price") or last_price
                place_range_grid_orders(state, last_price, anchor, grid_step_pct, equity_quote, step, min_notional)

            has_grid_positions = any(p["strategy"] == "grid" for p in state.get("positions", []))
            if regime == "RANGE" and not has_grid_positions and not state.get("open_buy_orders"):
                state["anchor_price"] = last_price

            if state.get("crash_mode_until_ts") and time.time() >= state["crash_mode_until_ts"]:
                state["crash_mode_until_ts"] = None

            log(
                f"price={last_price:.2f} anchor={state.get('anchor_price', last_price):.2f} regime={regime} "
                f"vol={volatility:.5f} step={grid_step_pct:.4f} spread={(spread if spread is not None else float('nan')):.5f} "
                f"equity≈{equity_quote:.2f} free_quote≈{free_quote:.2f} reserved_quote≈{paper_reserved_quote(state):.2f} "
                f"base≈{paper_total_base_balance(state):.6f} exp={exp_pct:.2%} cash={cash_pct:.2%} "
                f"open_buys={len(state.get('open_buy_orders', []))} positions={len(state.get('positions', []))} "
                f"realized≈{state.get('realized_pnl_quote', 0.0):.2f}"
            )

            if (time.time() - (state.get("last_heartbeat_ts") or 0)) >= HEARTBEAT_TELEGRAM_SECONDS:
                state["last_heartbeat_ts"] = time.time()
                t_send(f"Heartbeat: equity≈{equity_quote:.2f} {get_quote_code()} regime={regime}", "OTHER")

            save_state(state)
            time.sleep(POLL_SECONDS)

        except (ccxt.NetworkError, ccxt.RequestTimeout, ccxt.ExchangeError) as exc:
            log(f"exchange error: {exc}")
            time.sleep(POLL_SECONDS)
        except KeyboardInterrupt:
            save_state(state)
            raise
        except Exception as exc:
            log(f"fatal loop error: {exc}")
            save_state(state)
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()