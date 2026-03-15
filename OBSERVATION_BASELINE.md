# 稳定观察期基线记录

> **版本**: stable-observe-2026-03-14  
> **记录时间**: 2026-03-14 19:16 UTC+8  
> **基线Commit**: 1e16b43  
> **归档日期**: 2026-03-14 22:36

---

## 一、今日项目阶段结论

1. AI Quant Brain 当前主线仍为 Binance Demo Trading 的 BTC/USDT Grid Bot。
2. 当前阶段目标仍是"稳定运行观察"，不是激进扩展。
3. Dashboard V2 已完成并通过，菜单固定为：量化 / 资讯 / 宏观 / 监控 / 系统。
4. 项目已进入稳定观察期，除单点故障修复外，不继续扩展功能、不做大范围重构。
5. 自我进化模块 V1 已接入，但属于旁路进化链，不能自动修改生产参数或生产代码。

---

## 二、今日完成事项

| 序号 | 事项 | 状态 | Commit |
|------|------|------|--------|
| 1 | Dashboard V2 重构 (5菜单) | ✅ | ac12bfc, bf28b91 |
| 2 | 资讯页状态区分修复 | ✅ | c36dcf2, 6491f6d |
| 3 | Telegram 巡检/告警机制 | ✅ | cd80352, 094e453 |
| 4 | 量化模块 Bug 修复 | ✅ | cd80352 |
| 5 | Dashboard 数据源修复 | ✅ | 4782f3e |
| 6 | 自我进化模块 V1 上线 | ✅ | b23efcf |
| 7 | 进化模块评分 Bug 修复 (40→100) | ✅ | 1e16b43 |
| 8 | 稳定观察期基线文件 | ✅ | 8f88c86 |
| 9 | 宏观数据接入 V1 方案 | ✅ | cc9325e |
| 10 | freshness/告警分层规则修复 | ✅ | 61e68db |
| 11 | commander_status.json 排查收口 | ✅ | e8e41f3 |

---

## 三、今日关键结论

### 1. 进化模块评分问题
- 根因：strategy_evaluator.py 中 key 映射错误
- 结果：评分由 40/100 恢复到 100/100
- 说明：旁路评估链 bug，不是交易主链故障

### 2. upgrade gate 状态说明
- 修复前：BLOCKED
- 修复后：PENDING_APPROVAL
- 底线：不允许自动改生产参数或生产代码

### 3. 21:00 晚间巡检故障
- 根因：scheduler.py Python 路径错误 (3.7.3 缺 requests)
- 修复：改为 /usr/local/bin/python3 (3.11.2)
- 状态：已修复

### 4. freshness / 告警分层修复
- quant_report.json：高频 / critical / <30min
- commander_status.json：中频 / warning / <60min
- news/macro：低频 / info / <24h

### 5. commander_status.json 排查
- 生成：scripts/commander.py
- 机制：仅启动时生成一次
- 定性：设计留空的低活跃文件，非主链故障

---

## 四、当前项目边界

### 允许范围
- ✅ 单点故障修复
- ✅ 运行环境修复
- ✅ freshness/告警/监控类必要修正
- ✅ 文档补记

### 禁止范围
- ❌ 自动改生产参数/代码
- ❌ 大范围重构
- ❌ 新增无关功能
- ❌ 改 Dashboard 结构
- ❌ 宏观数据接入生产执行链

---

## 五、宏观数据接入边界

### 当前允许进入
- Dashboard 展示层
- 报告层
- advisor/commander 建议层

### 当前禁止进入
- Grid Bot 生产执行链
- 自动参数调整
- 自动生产代码变更

---

## 六、观察窗口

- **建议时长**: 7 天 (2026-03-14 ~ 2026-03-21)
- **最短**: 24 小时

---

## 七、观察重点

| 序号 | 观察项 |
|------|--------|
| 1 | 09:00 / 21:00 巡检自动发送 |
| 2 | Dashboard 数据刷新 |
| 3 | quant_report.json 高频有效 |
| 4 | Demo API 与本地状态一致 |
| 5 | 评分链稳定性 |
| 6 | current_commit 字段一致性 |

---

## 八、事件记录


| 项目 | 内容 |
|------|------|
| **时间** | 2026-03-15 10:37 |
| **现象** | 最后同步显示 2026-03-14 09:50 |
| **根因** | 前端从 commander_status.json 读取，但该文件无自动刷新 |
| **修复** | 改为从 quant_report.updated_at 读取 |
| **Commit** | b6edc5b |
| **状态** | 已合并到 master |

---

## 九、版本锚点

- **基线版本**: stable-observe-2026-03-14
- **基线 Commit**: 1e16b43
- **最新 Commit**: 8e1acc5

---

## 十、freshness / 告警链收口结论

### 问题描述
23:04 告警中 quant_report.json 仅 19 分钟却被判为"已过期"

### 根因
telegram_alert.py 使用旧逻辑：硬编码 5 分钟阈值，所有文件统一判断

### 修复
- health_check.py: 已分层 (commit 61e68db)
- telegram_alert.py: 改为分层阈值 (commit 63c56e5)

### 分层职责
- health_check.py: 细分检查层，区分正常/过期/缓存/超时/较旧
- telegram_alert.py: 告警输出层，判断是否告警

### 统一阈值
| 文件 | 阈值 | 说明 |
|------|------|------|
| quant_report.json | 30 分钟 | 交易主链严格标准 |
| commander_status.json | 240 分钟 | 系统状态 |
| news_report.json | 1440 分钟 | 低频资讯 |
| macro_report.json | 1440 分钟 | 低频宏观 |

### 正式口径
- 阈值边界一致
- 告警触发点一致
- 文案风格不同属于设计分层，不属于逻辑不一致

---

## 十一、归档结论

2026-03-14 当日版本已完成收口，AI Quant Brain 当前进入稳定观察期；主量化链正常，巡检链恢复，旁路评估链恢复，freshness/告警链已分层统一；除单点故障修复外，不再继续扩展。

---

*本文档为 2026-03-14 稳定观察期基线记录。*
