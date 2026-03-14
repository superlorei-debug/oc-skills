# 宏观数据接入实现方案 V1

> **版本**: macro-v1-2026-03-14  
> **目标**: 展示层 / 报告层 / advisor 层增强  
> **禁止**: 进入生产执行链

---

## 一、当前仓库评估

### 1.1 现有可复用结构

| 模块 | 位置 | 可复用程度 |
|------|------|------------|
| macro_report.json | data/latest/ | 高 - 已有基础结构 |
| news_report.json | data/latest/ | 高 - 已有抓取框架 |
| Dashboard 宏观页 | dashboard/index.html | 高 - 已有占位卡片 |
| Dashboard 监控页 | dashboard/index.html | 高 - 已有巡检/告警结构 |
| commander_status.json | data/latest/ | 中 - 可扩展宏观标签 |

### 1.2 现有占位符

Dashboard 宏观页面已有以下占位符：
- 📊 国家统计局 (CPI/PPI/PMI) - "📡 部分接入"
- 📋 宏观事件 - "⏳ 筹备中"

---

## 二、宏观指标接入方案

### 2.1 第一批指标清单

| 序号 | 指标 | 字段名 | 数据来源 | 更新频率 | 落点 |
|------|------|--------|----------|----------|------|
| 1 | 美联储利率 | fed_rate_upper / fed_rate_lower | CME FedWatch API | 日 | macro |
| 2 | 政策倾向 | fed_policy_bias | 推导/专家解读 | 日 | macro |
| 3 | 美国 CPI | us_cpi_yoy | tradingeconomics.com | 月 | macro |
| 4 | 核心 CPI | us_core_cpi_yoy | tradingeconomics.com | 月 | macro |
| 5 | 非农就业 | us_nfp | tradingeconomics.com | 月 | macro |
| 6 | 失业率 | us_unemployment_rate | tradingeconomics.com | 月 | macro |
| 7 | 美债 10Y | us10y_yield | Yahoo Finance | 日 | macro |
| 8 | VIX | vix_index | Yahoo Finance | 日 | macro |
| 9 | 美元指数 | dollar_index_broad | Yahoo Finance | 日 | macro |
| 10 | 中国制造业 PMI | cn_manufacturing_pmi | tradingeconomics.com | 月 | macro |
| 11 | 中国非制造业 PMI | cn_nonmanufacturing_pmi | tradingeconomics.com | 月 | macro |
| 12 | 中国 M2 同比 | cn_m2_yoy | tradingeconomics.com | 月 | macro |
| 13 | 中国社融 | cn_tsf_stock_yoy | tradingeconomics.com | 月 | macro |
| 14 | BTC ETF 净流入 | btc_etf_netflow_daily | Bloomberg/coinglass | 日 | 资讯-加密 |
| 15 | 稳定币市值 | stablecoin_marketcap_total | coin gecko | 日 | 资讯-加密 |

### 2.2 数据落点明细

#### macro_report.json 扩展
```json
{
  "updated_at": "2026-03-14 21:00",
  "macro_phase": "弱修复",
  "fed_rate": { "upper": 4.50, "lower": 4.25, "bias": "neutral" },
  "us_macro": { "cpi_yoy": 2.8, "core_cpi_yoy": 3.2, "nfp": 180, "unemployment": 4.0 },
  "rates": { "us10y_yield": 4.25 },
  "risk": { "vix_index": 16.5, "dollar_index": 103.5 },
  "china": { "manufacturing_pmi": 50.6, "m2_yoy": 7.0, "tsf_yoy": 9.5 },
  "crypto": { "etf_netflow_24h": 150000000, "stablecoin_mcap": 180000000000 },
  "labels": {
    "liquidity_regime": "中性",
    "risk_sentiment": "neutral",
    "usd_pressure": "中",
    "china_growth_state": "平稳",
    "crypto_flow_state": "流入"
  },
  "data_freshness": { "status": "ok", "last_full_update": "2026-03-14" }
}
```

#### Dashboard 宏观页面展示
- 左侧卡片: 美联储 / 美国数据 (fed_rate, us_macro)
- 中间卡片: 市场数据 (us10y, VIX, 美元指数)
- 右侧卡片: 中国数据 (PMI, M2, 社融)
- 底部: 加密市场 (ETF 净流入, 稳定币市值)

#### Dashboard 资讯页面扩展
- 加密市场卡片: BTC ETF 净流入 + 稳定币市值
- 金融市场卡片: VIX + 美元指数 + 10Y

#### commander_status.json 扩展 (advisor 层)
```json
{
  "macro": {
    "module_status": "executed",
    "data_freshness": "ok",
    "labels": {
      "liquidity_regime": "中性",
      "risk_sentiment": "neutral",
      "usd_pressure": "中",
      "china_growth_state": "平稳",
      "crypto_flow_state": "流入"
    },
    "last_update": "2026-03-14 21:00"
  }
}
```

---

## 三、标签系统设计

### 3.1 宏观标签定义

| 标签 | 取值 | 判断规则 |
|------|------|----------|
| liquidity_regime | 宽松 / 中性 / 收紧 | fed_rate < 3% = 宽松, 3-5% = 中性, > 5% = 收紧 |
| risk_sentiment | risk-on / neutral / risk-off | VIX < 15 = risk-on, 15-25 = neutral, > 25 = risk-off |
| usd_pressure | 高 / 中 / 低 | 美元指数 > 105 = 高, 100-105 = 中, < 100 = 低 |
| china_growth_state | 改善 / 平稳 / 走弱 | PMI > 51 = 改善, 49-51 = 平稳, < 49 = 走弱 |
| crypto_flow_state | 流入 / 中性 / 流出 | ETF 净流入 > 0 = 流入, < 0 = 流出 |

### 3.2 标签用途

- **展示**: Dashboard 宏观页面显示标签
- **报告**: quant_report / commander_status 包含宏观摘要
- **advisor**: 输出宏观建议，不进入执行链

---

## 四、监控层设计

### 4.1 数据新鲜度规则

| 数据类型 | 期望更新频率 | 过期阈值 | 显示状态 |
|----------|--------------|----------|----------|
| 美联储利率 | 日 | > 48h | 缓存 |
| 美国 CPI | 月 | > 35d | 缓存 |
| 中国 PMI | 月 | > 35d | 缓存 |
| VIX | 日 | > 24h | ✅ 正常 |
| 美元指数 | 日 | > 24h | ✅ 正常 |
| BTC ETF | 日 | > 24h | ✅ 正常 |
| 稳定币市值 | 日 | > 24h | ✅ 正常 |

### 4.2 抓取失败处理

- 单指标抓取失败: 该指标显示 `-`，不影响其他指标
- 全部失败: macro_report.json 保留上次数据，标记 `status: degraded`
- 监控页显示: 抓取状态 / 最后更新时间 / 各指标新鲜度

---

## 五、实现路径

### 5.1 V1 实现范围 (可落地)

| 序号 | 内容 | 文件 | 优先级 |
|------|------|------|--------|
| 1 | macro_report.py 抓取脚本 | scripts/macro_report.py | P0 |
| 2 | 更新 data/latest/macro_report.json | - | P0 |
| 3 | Dashboard 宏观页面展示增强 | dashboard/index.html | P1 |
| 4 | commander_status.json 宏观标签 | scripts/commander.py | P1 |
| 5 | 监控页数据状态显示 | dashboard/index.html | P2 |

### 5.2 V2 待实现 (方案设计)

| 序号 | 内容 | 说明 |
|------|------|------|
| 1 | 更多宏观指标接入 | PPI/零售/房价等 |
| 2 | 历史数据存储 | data/macro/history/ |
| 3 | 趋势分析 | 环比/同比变化 |
| 4 | 自动报告生成 | 宏观周报/月报 |

### 5.3 数据源风险标注

| 风险 | 说明 | 应对 |
|------|------|------|
| tradingeconomics 可能限速 | 免费 API 有请求限制 | 缓存 + 最小请求 |
| Yahoo Finance 可能不稳定 | 偶尔 403 | 备用数据源 |
| 月度数据更新延迟 | CPI/PMI 月末发布 | 显示发布日期 |
| 口经差异 | 不同数据源口径可能不同 | 标注数据来源 |

---

## 六、边界约束

### 6.1 允许范围

- ✅ Dashboard 宏观页面展示增强
- ✅ macro_report.json 数据扩展
- ✅ commander_status.json 宏观标签
- ✅ 资讯页面加密市场卡片
- ✅ 监控页面数据状态

### 6.2 禁止范围

- ❌ 宏观数据进入 Grid Bot 下单逻辑
- ❌ 宏观标签自动触发交易
- ❌ 修改 grid_bot.py 参数
- ❌ 通过 evolution 模块改生产代码

---

## 七、后续接入顺序

1. **第一阶段**: 美债 10Y + VIX + 美元指数 (日频，易获取)
2. **第二阶段**: 稳定币市值 + BTC ETF 净流入 (加密相关)
3. **第三阶段**: 美联储利率 + CPI (月频，官方数据)
4. **第四阶段**: 中国 PMI + M2 + 社融 (月频)

---

*本方案仅用于展示层/报告层/advisor 层增强，不进入生产执行链。*
