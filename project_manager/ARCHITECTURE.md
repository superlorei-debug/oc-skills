# ⚠️ 系统架构文档 (已过时)

> **注意**：本文档已严重过时，暂不作为当前项目的正式依据。  
> 当前项目的状态协议请参考：[PROTOCOL.md](../../PROTOCOL.md)  
> 当前项目的运行指南请参考：[RUN_GUIDE.md](../../RUN_GUIDE.md)

## 概述

本文档记录财富管家系统的整体架构，包括各模块职责、数据流向和接口定义。

## 模块架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Telegram 用户端                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Commander 主控模块                        │
│                 (scripts/commander.py)                     │
│  - 统一入口，整合量化/新闻/宏观                             │
│  - 风险等级计算                                            │
│  - 总判断逻辑                                              │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌───────────────────┬───────────────────┬───────────────────┐
        ▼                   ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   Quant      │   │    News      │   │    Macro     │   │  Dashboard   │
│   量化模块   │   │   新闻模块    │   │   宏观模块    │   │   看板展示   │
│              │   │              │   │              │   │              │
│ scripts/    │   │ scripts/    │   │ scripts/    │   │ dashboard/  │
│ quant_      │   │ news_       │   │ macro_      │   │ index.html  │
│ report.py   │   │ report.py    │   │ report.py   │   │              │
└───────────────┘   └───────────────┘   └───────────────┘   └───────────────┘
        │                   │                   │                   │
        ▼                   ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  Binance API │   │ 免费RSS源    │   │ 静态分析     │   │ data/latest/ │
│  (模拟盘)    │   │ (Fed/SEC)    │   │ (V1简化版)   │   │   JSON数据   │
└───────────────┘   └───────────────┘   └───────────────┘   └───────────────┘
```

## 模块职责

### 1. Quant 量化模块

**文件**: `scripts/quant_report.py`

**职责**:
- 监控网格交易策略状态
- 计算资金利用率、库存层数
- 生成盈亏报告
- 风险预警

**数据源**: Binance API (模拟盘)

**输出字段**:
- price_usd, position_btc
- inventory_layers_used, inventory_layers_limit
- total_u, used_u, remaining_u
- capital_utilization_pct
- today_pnl_u, yesterday_pnl_u
- status (critical/warning/ok)

---

### 2. News 新闻模块

**文件**: `scripts/news_report.py`

**职责**:
- 抓取高可信新闻源 (Federal Reserve, SEC, CoinDesk)
- 分析市场影响
- 评估对BTC/量化策略的影响

**数据源**: 免费 RSS 源

**输出字段**:
- fetch_mode (实时/缓存/无数据)
- articles[].title, source, credibility
- articles[].core_content, market_impact, btc_strategy_impact

---

### 3. Macro 宏观模块

**文件**: `scripts/macro_report.py`

**职责**:
- 宏观阶段判断 (弱修复/偏弱/结构分化/温和回暖)
- 家庭理财建议生成
- 风险偏好评估

**数据源**: 静态分析 (V1简化版)

**输出字段**:
- macro_phase, macro_phase_definition
- judgement_reasons[]
- family_strategy, family_strategy_definition
- implications[]
- one_line_advice

---

### 4. Commander 主控模块

**文件**: `scripts/commander.py`

**职责**:
- 整合三大模块数据
- 计算总体风险等级
- 生成统一简报
- 支持简版/详细版输出
- 自然语言触发识别

**输入**: Quant, News, Macro 模块输出

**输出**:
- overall_risk_level (critical/warning/ok)
- overall_advice
- judgement_basis

---

### 5. Dashboard 展示层

**文件**: `dashboard/index.html`

**职责**:
- 可视化展示系统状态
- 4个页面: 总览/量化/新闻/宏观
- 自动刷新 (30秒)
- 响应式布局

**数据源**: `data/latest/*.json`

---

## 数据流

```
1. 用户请求 → Commander
2. Commander 调用各子模块脚本
3. 子模块解析命令行输出
4. gen_dashboard_data.py 生成 JSON
5. Dashboard 读取 JSON 展示
```

## 部署结构

```
openclaw-project/
├── scripts/
│   ├── commander.py       # 主控
│   ├── quant_report.py    # 量化
│   ├── news_report.py     # 新闻
│   ├── macro_report.py    # 宏观
│   └── gen_dashboard_data.py  # 数据生成
├── data/
│   └── latest/           # JSON数据
│       ├── commander_summary.json
│       ├── quant_report.json
│       ├── news_report.json
│       └── macro_report.json
└── dashboard/
    └── index.html        # 看板
```

## 接口规范

### JSON 字段命名规范

- 时间字段: `updated_at` (ISO格式)
- 状态枚举: `status` (critical/warning/ok)
- 金额字段: 数字类型，单位后缀如 `_u`, `_pct`
- 布尔字段: `is_xxx` 或 `has_xxx`

### 状态颜色映射

| 状态 | 颜色 | CSS类 |
|------|------|--------|
| critical | 红色 | danger |
| warning | 黄色 | warning |
| ok | 绿色 | success |
| 无数据 | 灰色 | info |

---

*最后更新: 2026-03-12*
