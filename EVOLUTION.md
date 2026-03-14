# AI Quant Brain 自我进化模块

本文档记录 AI Quant Brain 的自我进化与策略评估旁路链模块。

---

## 概述

**设计原则**："主交易链稳定，旁路进化链学习。"

本模块是现有 AI Quant Brain 架构的**旁路扩展**，不参与主交易流程，仅负责：
- 观察系统运行
- 评估策略表现
- 分析市场状态
- 生成参数建议
- 管理升级闸门

---

## 与主架构的关系

### 主交易链（稳定）
```
策略层 → 执行层 → Binance API → 数据层 → Dashboard/Telegram
```

### 旁路进化链（学习）
```
数据层 → 交易日志 → 策略评估 → 市场识别 → 参数实验室 → 升级闸门
```

### 边界定义
- **主交易链**：负责实际下单、撤单、状态同步
- **旁路进化链**：负责观察、学习、建议，不直接干预主链

---

## 模块组成

### 1. Trade Journal (交易日志)
- 记录结构化交易事件
- 用于后续策略评估
- 不影响主状态文件

**输出**: `data/evolution/trade_journal.json`

### 2. Strategy Evaluator (策略评估器)
- 对当前策略打分
- 稳定性 / 表现 / 风控三维评估
- 输出综合评分和建议

**输出**: `data/evolution/strategy_score.json`

### 3. Market Regime Detector (市场状态识别)
- 粗颗粒度市场分类
- 震荡 / 上行 / 下行 / 高波动 / 风险事件 / 稳定
- 为参数建议提供市场上下文

**输出**: `data/evolution/market_regime.json`

### 4. Parameter Lab (参数实验室)
- 生成候选参数方案
- 保守 / 均衡 / 激进
- 不自动生效，仅输出建议

**输出**: `data/evolution/parameter_candidates.json`

### 5. Upgrade Gate (升级闸门)
- V1 框架：默认不自动升级
- 检查禁止条件
- 决策：BLOCKED / PENDING_APPROVAL / APPROVED

**输出**: `data/evolution/upgrade_decision.json`

---

## V1 功能边界

### ✅ 已实现
- 交易日志记录
- 策略评分（稳定性/表现/风控）
- 市场状态识别（6类）
- 参数建议生成（3套方案）
- 升级闸门框架

### ❌ V1 不做
- 不自动改生产参数
- 不绕过人工确认
- 不插进主下单流程
- 不修改 commander_status.json / quant_report.json

---

## 数据输出

| 文件 | 位置 | 说明 |
|------|------|------|
| trade_journal.json | data/evolution/ | 交易事件日志 |
| strategy_score.json | data/evolution/ | 策略评分 |
| market_regime.json | data/evolution/ | 市场状态 |
| parameter_candidates.json | data/evolution/ | 参数建议 |
| upgrade_decision.json | data/evolution/ | 升级决策 |

---

## 运行方式

```bash
# 运行全部进化模块
python3 scripts/evolution/__init__.py

# 单独运行
python3 scripts/evolution/trade_journal.py
python3 scripts/evolution/strategy_evaluator.py
python3 scripts/evolution/market_regime_detector.py
python3 scripts/evolution/parameter_lab.py
python3 scripts/evolution/evolution_main.py
```

---

## 配置

### 升级闸门条件
- 最低评分: 70分
- 禁止升级条件: 数据无效 / API异常 / 模式降级

### 默认行为
- 自动应用: 否
- 人工审批: 是

---

## 后续路线

### V2 (规划)
- 回测接口
- 模拟交易验证
- 参数自动测试

### V3 (规划)
- A/B Testing 框架
- 自动升级（需审批）
- 性能追踪

---

*最后更新: 2026-03-14*
