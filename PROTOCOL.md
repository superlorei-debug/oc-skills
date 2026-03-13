# AI Quant Brain 状态协议文档

本文档记录 AI Quant Brain 系统的状态字段、数据结构、JSON 协议，是代码实现的正式依据。

---

## 1. 核心原则

### 1.1 单源原则
- 代码只有一份源码：`scripts/`
- 运行目录通过符号链接指向源码
- 状态文件统一写入：`data/latest/`

### 1.2 状态一致性原则
- Telegram 输出、Dashboard 显示、JSON 文件使用同一套字段
- 失败值统一为 `null`，不伪装成 0

---

## 2. 目录结构

```
~/openclaw-project/
├── scripts/              # 源码目录 (单源)
│   ├── grid_bot.py      # 网格机器人
│   ├── commander.py    # 主控汇总
│   ├── quant_report.py # 量化报告
│   ├── health_check.py # 健康巡检
│   └── demo_api_manager.py # Demo API 管理
├── runs/grid_bot/       # 运行目录
│   └── bot.py -> ../../scripts/grid_bot.py  # 符号链接
├── data/latest/         # 状态文件目录
│   ├── commander_status.json
│   ├── quant_report.json
│   ├── news_report.json
│   └── macro_report.json
├── deploy/              # 部署脚本
│   ├── run_bot.sh
│   ├── restart_bot.sh
│   └── stop_bot.sh
└── logs/               # 日志目录
```

---

## 3. commander_status.json 字段定义

### 3.1 顶层字段

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| schema_version | string | 协议版本 | "v1" |
| generated_at | string | 生成时间 (ISO) | "2026-03-13T20:00:00Z" |
| overall_status | string | 总体状态 | "ok" / "warning" / "degraded" / "critical" |

### 3.2 runtime 运行时信息

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| runtime.current_commit | string | Git commit | "78570a1" |
| runtime.runtime_path | string | 运行文件路径 | "scripts/grid_bot.py" |
| runtime.start_time | string | 启动时间 | "2026-03-13T19:00:00Z" |
| runtime.target_mode | string | 目标模式 | "binance_demo" |
| runtime.actual_mode | string | 实际模式 | "binance_demo" |
| runtime.degrade_reason | string/null | 降级原因 | null / "Demo API 502" |

### 3.3 quant 量化模块

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| quant.module_execution_status | string | 执行状态 | "executed" / "failed" / "degraded" |
| quant.target_mode | string | 目标模式 | "binance_demo" |
| quant.actual_mode | string/null | 实际模式 | "paper" |
| quant.degrade_reason | string/null | 降级原因 | "Demo API 502" |
| quant.account_data_status | string/null | 账户数据状态 | "success" / "failed" |
| quant.market_data_status | string/null | 市场数据状态 | "success" / "failed" |
| quant.order_data_status | string/null | 订单数据状态 | "success" / "failed" |
| quant.data_validity | boolean | 数据有效性 | true / false |
| quant.last_success_sync | string/null | 最后成功同步时间 | "2026-03-13 20:00" |

### 3.4 quant.data 量化数据

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| quant.data.price | float/null | BTC 价格 | 72224.51 |
| quant.data.balance_usdt | float/null | USDT 余额 | 4826.43 |
| quant.data.position_btc | float/null | BTC 持仓 | 0.0 |
| quant.data.layers_used | int/null | 已用层数 | 1 |
| quant.data.layers_limit | int/null | 最大层数 | 6 |
| quant.data.utilization_pct | float/null | 资金利用率 | 3.6 |
| quant.data.orders_count | int/null | 挂单数量 | 1 |
| quant.data.status | string/null | 状态 | "ok" / "warning" / "critical" |

### 3.5 system 系统状态

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| system.bot.running | boolean | Bot 是否运行 | true |
| system.bot.pid | string | 进程 PID | "59890" |
| system.demo_api.connected | boolean | Demo API 连接 | true |
| system.demo_api.latency_ms | int | 延迟 | 463 |

---

## 4. 数据新鲜度规则

### 4.1 freshness 状态

| 值 | 说明 | 条件 |
|----|------|------|
| fresh | 正常 | data_validity=true 且 last_success_sync < 30分钟 |
| stale | 过期 | data_validity=true 且 30分钟 <= age < 120分钟 |
| expired | 过期 | data_validity=true 且 age >= 120分钟 |
| invalid | 无效 | data_validity=false 或无同步记录 |

### 4.2 overall_status 状态

| 值 | 说明 | 条件 |
|----|------|------|
| ok | 正常 | data_validity=true 且 freshness=fresh 且 demo_api.connected=true |
| warning | 警告 | data_validity=false 或 freshness=invalid/expired |
| degraded | 降级 | demo_api.connected=false |
| critical | 危险 | quant.data.status=critical |

---

## 5. Demo API 降级机制

### 5.1 三条链分离

| 链 | 类型 | 接口 |
|----|------|------|
| market | 行情读取 | /api/v3/ticker/price |
| account | 账户读取 | /api/v3/account |
| order | 订单交易 | /api/v3/order, /api/v3/openOrders |

### 5.2 熔断触发条件

- 连续 3 次订单操作失败
- 连续 3 次账户读取失败
- 连续 3 次市场数据失败

### 5.3 降级表现

| 状态 | 说明 |
|------|------|
| target_mode | 配置文件中的目标模式 |
| actual_mode | 实际运行模式 (binance_demo / paper) |
| degrade_reason | 降级原因描述 |

---

## 6. Telegram 输出模板

### 6.1 今日关注详细版

触发词: "今天需要注意什么" / "今日关注" / "详细版"

```
一、今日重点摘要
├─ 总体状态：⚠️ 警告 / ✅ 正常
├─ 首要问题：...

二、量化交易
├─ 数据新鲜度：✅ 正常 / ⚠️ 过期 / 🔴 无效
├─ 数据有效性：有效 / 无效
├─ 最后成功同步：2026-03-13 20:00
├─ BTC 价格：$72,224.51
├─ USDT 余额：4826.43
...

三、新闻与地缘
├─ 状态：已执行
├─ 模式：实时 / 缓存
└─ 新闻数量：...

四、宏观环境
├─ 状态：已执行
├─ 宏观阶段：弱修复
...

五、系统运行
├─ Bot 进程：✅ 运行中
├─ 目标模式：binance_demo
├─ 实际模式：binance_demo / paper
├─ Demo API：✅ 正常 / ❌ 异常
└─ 降级原因：...

六、今日动作建议
├─ 1. ...
```

### 6.2 巡检模板

触发词: "系统状态" / "巡检" / "健康检查"

```
【AI Quant Brain｜健康巡检】
【1. 运行路径】
【2. 版本信息】
【3. 交易安全状态】
【4. Bot 进程】
```

---

## 7. 命令汇总

### 7.1 启动
```bash
cd ~/openclaw-project/runs/grid_bot
python3 bot.py &
```

### 7.2 重启
```bash
bash ~/openclaw-project/deploy/restart_bot.sh
```

### 7.3 查看状态
```bash
cat ~/openclaw-project/data/latest/commander_status.json | python3 -m json.tool
```

### 7.4 手动执行报告
```bash
# 今日关注详细版
python3 scripts/commander.py "今天需要注意什么详细版"

# 巡检
python3 scripts/commander.py "系统状态"

# 量化报告
python3 scripts/quant_report.py
```

---

## 8. 附录

### 8.1 状态映射 (Dashboard)

| JSON 值 | 显示 | CSS 类 |
|--------|------|--------|
| ok | 正常 | success |
| warning | 预警 | warning |
| degraded | 降级 | danger |
| critical | 危险 | danger |
| fresh | 正常 | success |
| stale | 过期 | warning |
| expired | 过期 | danger |
| invalid | 无效 | danger |

### 8.2 文件路径

- 源码: `~/openclaw-project/scripts/`
- 运行: `~/openclaw-project/runs/grid_bot/`
- 状态: `~/openclaw-project/data/latest/`
- 日志: `~/openclaw-project/logs/`
- 部署: `~/openclaw-project/deploy/`

---

*最后更新: 2026-03-13*
*版本: v1*
