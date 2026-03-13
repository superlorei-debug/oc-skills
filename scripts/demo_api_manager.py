#!/usr/bin/env python3
"""
Binance Demo API Manager
工程化容错处理 - 熔断、降级、恢复机制
"""
import os
import time
import json
import threading
import requests
import hmac
import hashlib
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict


class APIChainType(Enum):
    """API 调用链类型"""
    MARKET = "market"      # 行情读取
    ACCOUNT = "account"   # 账户读取
    ORDER = "order"       # 订单交易


class APIModeStatus(Enum):
    """API 状态"""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CIRCUIT_BROKEN = "circuit_broken"


@dataclass
class APIChainStatus:
    """单条链的状态"""
    chain_type: str
    status: str = "unknown"
    last_success_ts: float = 0
    last_error: str = ""
    consecutive_failures: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    
    def is_healthy(self) -> bool:
        return self.status == "healthy"
    
    def record_success(self):
        self.status = "healthy"
        self.last_success_ts = time.time()
        self.consecutive_failures = 0
    
    def record_failure(self, error: str):
        self.status = "failed"
        self.last_error = error
        self.consecutive_failures += 1
        self.failed_requests += 1


@dataclass
class DemoAPIState:
    """Demo API 全局状态"""
    # 目标模式
    target_mode: str = "binance_demo"
    
    # 实际模式
    actual_mode: str = "paper"
    
    # 降级原因
    degrade_reason: str = ""
    
    # 熔断触发
    circuit_broken: bool = False
    circuit_break_ts: float = 0
    circuit_break_reason: str = ""
    
    # 三条链状态
    market_chain: APIChainStatus = field(default_factory=lambda: APIChainStatus("market"))
    account_chain: APIChainStatus = field(default_factory=lambda: APIChainStatus("account"))
    order_chain: APIChainStatus = field(default_factory=lambda: APIChainStatus("order"))
    
    # 最后同步时间
    last_balance_sync: str = ""
    last_order_sync: str = ""
    last_price_sync: str = ""
    
    # 订单请求记录（防重复）
    pending_requests: Dict[str, dict] = field(default_factory=dict)
    
    # 熔断配置
    CIRCUIT_BREAK_THRESHOLD = 3  # 连续失败次数
    RECOVERY_CHECK_INTERVAL = 60  # 恢复检查间隔（秒）


class DemoAPIManager:
    """Demo API 管理器"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://demo-api.binance.com"
        
        self.state = DemoAPIState()
        self._lock = threading.Lock()
        
        # 结构化日志
        self.logs: List[dict] = []
        self._max_logs = 1000
    
    def _sign(self, query: str) -> str:
        return hmac.new(
            self.api_secret.encode(), 
            query.encode(), 
            hashlib.sha256
        ).hexdigest()
    
    def _request(self, method: str, endpoint: str, params: dict = None, chain: APIChainType = None) -> Optional[dict]:
        """统一请求处理"""
        ts = int(time.time() * 1000)
        
        if params:
            query = "&".join([f"{k}={v}" for k, v in params.items()])
            query += f"&timestamp={ts}&recvWindow=10000"
        else:
            query = f"timestamp={ts}&recvWindow=10000"
        
        signature = self._sign(query)
        url = f"{self.base_url}{endpoint}?{query}&signature={signature}"
        headers = {"X-MBX-APIKEY": self.api_key}
        
        # 记录日志
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "endpoint": endpoint,
            "chain": chain.value if chain else "unknown",
            "status_code": None,
            "error": None,
            "retry": False,
            "circuit_broken": self.state.circuit_broken,
            "target_mode": self.state.target_mode,
            "actual_mode": self.state.actual_mode,
        }
        
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                resp = requests.post(url, headers=headers, timeout=10)
            elif method == "DELETE":
                resp = requests.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            log_entry["status_code"] = resp.status_code
            
            if resp.status_code >= 400:
                error_msg = resp.text[:100]
                log_entry["error"] = error_msg
                self._record_failure(chain, error_msg)
                self._log(log_entry)
                return None
            
            self._record_success(chain)
            log_entry["error"] = None
            self._log(log_entry)
            return resp.json()
            
        except requests.exceptions.Timeout:
            error = "Request timeout"
            log_entry["error"] = error
            self._record_failure(chain, error)
            self._log(log_entry)
            return None
        except requests.exceptions.ConnectionError as e:
            error = f"Connection error: {str(e)[:50]}"
            log_entry["error"] = error
            self._record_failure(chain, error)
            self._log(log_entry)
            return None
        except Exception as e:
            error = str(e)[:100]
            log_entry["error"] = error
            self._record_failure(chain, error)
            self._log(log_entry)
            return None
    
    def _record_success(self, chain: APIChainType):
        """记录成功"""
        with self._lock:
            if chain == APIChainType.MARKET:
                self.state.market_chain.record_success()
                self.state.last_price_sync = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            elif chain == APIChainType.ACCOUNT:
                self.state.account_chain.record_success()
                self.state.last_balance_sync = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            elif chain == APIChainType.ORDER:
                self.state.order_chain.record_success()
                self.state.last_order_sync = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 检查是否可以恢复
            self._check_recovery()
    
    def _record_failure(self, chain: APIChainType, error: str):
        """记录失败"""
        with self._lock:
            if chain == APIChainType.MARKET:
                self.state.market_chain.record_failure(error)
                self._check_circuit_break(APIChainType.MARKET)
            elif chain == APIChainType.ACCOUNT:
                self.state.account_chain.record_failure(error)
                self._check_circuit_break(APIChainType.ACCOUNT)
            elif chain == APIChainType.ORDER:
                self.state.order_chain.record_failure(error)
                self._check_circuit_break(APIChainType.ORDER)
    
    def _check_circuit_break(self, chain: APIChainType):
        """检查是否触发熔断"""
        if chain == APIChainType.MARKET:
            failures = self.state.market_chain.consecutive_failures
        elif chain == APIChainType.ACCOUNT:
            failures = self.state.account_chain.consecutive_failures
        elif chain == APIChainType.ORDER:
            failures = self.state.order_chain.consecutive_failures
        else:
            return
        
        # 订单链连续失败触发熔断
        if chain == APIChainType.ORDER and failures >= self.state.CIRCUIT_BREAK_THRESHOLD:
            self._trigger_circuit_break(f"连续{self.state.CIRCUIT_BREAK_THRESHOLD}次订单操作失败")
        
        # 账户链连续失败触发熔断
        if chain == APIChainType.ACCOUNT and failures >= self.state.CIRCUIT_BREAK_THRESHOLD:
            self._trigger_circuit_break(f"连续{self.state.CIRCUIT_BREAK_THRESHOLD}次账户读取失败")
    
    def _trigger_circuit_break(self, reason: str):
        """触发熔断"""
        if not self.state.circuit_broken:
            self.state.circuit_broken = True
            self.state.circuit_break_ts = time.time()
            self.state.circuit_break_reason = reason
            self.state.actual_mode = "paper"
            self.state.degrade_reason = reason
            
            # 记录熔断日志
            self._log({
                "event": "circuit_break",
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            })
    
    def _check_recovery(self):
        """检查是否可以恢复"""
        if not self.state.circuit_broken:
            return
        
        # 检查是否满足恢复条件
        can_recover = (
            self.state.market_chain.is_healthy() and
            self.state.account_chain.is_healthy()
        )
        
        if can_recover:
            self._log({
                "event": "recovery_available",
                "timestamp": datetime.now().isoformat(),
            })
    
    def _log(self, entry: dict):
        """结构化日志"""
        self.logs.append(entry)
        if len(self.logs) > self._max_logs:
            self.logs = self.logs[-self._max_logs:]
    
    def health_check(self) -> Dict[str, Any]:
        """启动前健康检查"""
        results = {
            "passed": False,
            "checks": [],
            "conclusion": "",
        }
        
        # 1. 基础连通性检查
        try:
            resp = requests.get(f"{self.base_url}/api/v3/ping", timeout=5)
            if resp.status_code == 200:
                results["checks"].append({"name": "ping", "status": "pass"})
            else:
                results["checks"].append({"name": "ping", "status": "fail", "error": f"HTTP {resp.status_code}"})
        except Exception as e:
            results["checks"].append({"name": "ping", "status": "fail", "error": str(e)[:50]})
        
        # 2. 账户读取检查
        account_data = self._request("GET", "/api/v3/account", chain=APIChainType.ACCOUNT)
        if account_data:
            results["checks"].append({"name": "account_read", "status": "pass"})
        else:
            results["checks"].append({"name": "account_read", "status": "fail", "error": self.state.account_chain.last_error})
        
        # 3. 订单接口可用性检查（只探测不下单）
        # 通过查询 open orders 来验证
        orders = self._request("GET", "/api/v3/openOrders", {"symbol": "BTCUSDT"}, APIChainType.ORDER)
        if orders is not None:
            results["checks"].append({"name": "order_read", "status": "pass"})
        else:
            results["checks"].append({"name": "order_read", "status": "fail", "error": self.state.order_chain.last_error})
        
        # 结论
        all_passed = all(c["status"] == "pass" for c in results["checks"])
        results["passed"] = all_passed
        
        if all_passed:
            results["conclusion"] = "健康检查通过，允许进入 binance_demo 交易状态"
            self.state.actual_mode = "binance_demo"
            self.state.degrade_reason = ""
        else:
            results["conclusion"] = "健康检查失败，自动降级到 paper 模式"
            self.state.actual_mode = "paper"
            self.state.degrade_reason = "启动健康检查失败"
        
        return results
    
    def get_price(self) -> Optional[float]:
        """获取价格（行情链）"""
        data = self._request("GET", "/api/v3/ticker/price", {"symbol": "BTCUSDT"}, APIChainType.MARKET)
        if data:
            return float(data.get("price", 0))
        return None
    
    def get_balance(self) -> Optional[dict]:
        """获取余额（账户链）"""
        data = self._request("GET", "/api/v3/account", chain=APIChainType.ACCOUNT)
        if data:
            balances = {b['asset']: float(b['free']) for b in data.get('balances', [])}
            return {
                'USDT': balances.get('USDT', 0),
                'USDC': balances.get('USDC', 0),
                'BTC': balances.get('BTC', 0),
            }
        return None
    
    def get_open_orders(self) -> List[dict]:
        """获取挂单（订单链）"""
        data = self._request("GET", "/api/v3/openOrders", {"symbol": "BTCUSDT"}, APIChainType.ORDER)
        if data:
            return [o for o in data if o.get('side') == 'BUY' and o.get('status') == 'NEW']
        return []
    
    def place_order(self, price: float, amount: float, client_order_id: str = None) -> Optional[dict]:
        """下单（订单链）- 防重复"""
        # 生成请求 ID
        if not client_order_id:
            client_order_id = f"grid_{int(time.time()*1000)}"
        
        # 检查是否已存在pending请求
        if client_order_id in self.state.pending_requests:
            pending = self.state.pending_requests[client_order_id]
            # 查询订单状态确认
            existing_orders = self.get_open_orders()
            for o in existing_orders:
                if o.get('clientOrderId') == client_order_id:
                    # 订单已存在，返回
                    return o
            
            # 订单不存在，可能是失败了，允许重试
            del self.state.pending_requests[client_order_id]
        
        # 记录pending请求
        self.state.pending_requests[client_order_id] = {
            "price": price,
            "amount": amount,
            "ts": time.time(),
        }
        
        params = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "type": "LIMIT",
            "quantity": str(amount),
            "price": str(int(price)),
            "timeInForce": "GTC",
            "newClientOrderId": client_order_id,
        }
        
        data = self._request("POST", "/api/v3/order", params, APIChainType.ORDER)
        
        if data:
            # 成功，移除pending
            self.state.pending_requests.pop(client_order_id, None)
            return data
        else:
            # 失败，不删除pending（等待查询确认）
            return None
    
    def cancel_order(self, order_id: str, client_order_id: str = None) -> bool:
        """撤单（订单链）- 防重复"""
        # 检查是否已存在pending请求
        cancel_key = f"cancel_{order_id}"
        if cancel_key in self.state.pending_requests:
            return False  # 已请求过
        
        self.state.pending_requests[cancel_key] = {"ts": time.time()}
        
        params = {
            "symbol": "BTCUSDT",
            "orderId": str(order_id),
        }
        
        data = self._request("DELETE", "/api/v3/order", params, APIChainType.ORDER)
        
        self.state.pending_requests.pop(cancel_key, None)
        return data is not None
    
    def attempt_recovery(self) -> Dict[str, Any]:
        """尝试恢复"""
        recovery_result = {
            "success": False,
            "steps": [],
        }
        
        if not self.state.circuit_broken:
            recovery_result["steps"].append({"step": "check", "status": "not_in_circuit_break"})
            return recovery_result
        
        # 1. 检查 API 恢复
        api_recovered = self._request("GET", "/api/v3/ping", chain=APIChainType.MARKET)
        if not api_recovered:
            recovery_result["steps"].append({"step": "api_check", "status": "fail"})
            return recovery_result
        recovery_result["steps"].append({"step": "api_check", "status": "pass"})
        
        # 2. 重新拉余额
        balance = self.get_balance()
        if not balance:
            recovery_result["steps"].append({"step": "balance_sync", "status": "fail"})
            return recovery_result
        recovery_result["steps"].append({"step": "balance_sync", "status": "pass", "data": balance})
        
        # 3. 重新拉挂单
        orders = self.get_open_orders()
        recovery_result["steps"].append({"step": "order_sync", "status": "pass", "count": len(orders)})
        
        # 4. 状态恢复
        self.state.circuit_broken = False
        self.state.actual_mode = "binance_demo"
        self.state.degrade_reason = ""
        
        recovery_result["success"] = True
        recovery_result["steps"].append({"step": "mode_restore", "status": "pass", "mode": "binance_demo"})
        
        return recovery_result
    
    def get_status(self) -> dict:
        """获取当前状态"""
        return {
            "target_mode": self.state.target_mode,
            "actual_mode": self.state.actual_mode,
            "circuit_broken": self.state.circuit_broken,
            "degrade_reason": self.state.degrade_reason,
            "chains": {
                "market": asdict(self.state.market_chain),
                "account": asdict(self.state.account_chain),
                "order": asdict(self.state.order_chain),
            },
            "last_sync": {
                "price": self.state.last_price_sync,
                "balance": self.state.last_balance_sync,
                "orders": self.state.last_order_sync,
            },
            "can_trade": (
                self.state.actual_mode == "binance_demo" and 
                not self.state.circuit_broken and
                self.state.order_chain.is_healthy()
            ),
        }
    
    def get_logs(self, limit: int = 100) -> List[dict]:
        """获取日志"""
        return self.logs[-limit:]


# 全局实例
_demo_api_manager: Optional[DemoAPIManager] = None


def init_demo_api_manager(api_key: str, api_secret: str) -> DemoAPIManager:
    """初始化 Demo API 管理器"""
    global _demo_api_manager
    _demo_api_manager = DemoAPIManager(api_key, api_secret)
    return _demo_api_manager


def get_demo_api_manager() -> Optional[DemoAPIManager]:
    """获取 Demo API 管理器"""
    return _demo_api_manager
