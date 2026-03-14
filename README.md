# AI Quant Brain

基于 OpenClaw 的 AI 量化交易与信息分析工程项目。

当前核心运行主线为 **Binance Demo Trading 环境下的 BTC/USDT Grid Bot**。  
现阶段以 **稳定性验证** 为第一优先级，重点关注系统稳定运行、订单行为正确、状态同步准确，以及 Dashboard 与交易所数据一致。

---

## 文档体系

> **重要**：本项目文档分为多个层次，各有明确用途：

| 文档 | 用途 | 优先级 |
|------|------|--------|
| **PROTOCOL.md** | 状态字段协议标准 | ⭐⭐⭐ 最高 |
| **RUN_GUIDE.md** | 运行/部署操作指南 | ⭐⭐⭐ 最高 |
| **README.md** | 项目概览 | ⭐⭐ 中 |
| ARCHITECTURE.md | 架构说明 | ⭐ 已过时，暂不作为依据 |

---

## 当前状态

- **交易所**：Binance
- **运行模式**：Demo Trading (binance_demo)
- **交易对**：BTC/USDT
- **策略类型**：Grid Bot
- **当前阶段**：Demo 验证阶段
- **验证周期**：1–2 个月

### 当前重点

- 系统稳定运行
- 订单行为正确
- 状态同步准确
- Dashboard 与交易所数据一致
- Demo API 异常自动降级

### 当前暂不优先

- 直接上实盘
- 增加复杂功能

---

## 系统架构

```text
策略层 → 执行层 → Binance API → 数据层 → Dashboard
```

### 架构说明

- **策略层**：负责网格策略逻辑与运行规则
- **执行层**：负责下单、撤单、查单与执行控制
- **Binance API**：负责账户、行情、订单交互
- **数据层**：负责状态持久化、报告生成与运行记录
- **Dashboard**：负责展示交易数据、系统状态及后续分析结果
---

## Dashboard 驾驶舱

### 导航结构

| 菜单 | 说明 | 真实数据 | 占位模块 |
|------|------|----------|----------|
| **量化** | 量化交易详情 | ✅ 全部 | - |
| **资讯** | 新闻与市场 | ✅ 突发新闻 | 加密/金融/地缘 |
| **宏观** | 宏观数据 | ✅ 部分 | 国家统计局/宏观事件 |
| **监控** | 巡检/告警/健康 | ✅ 部分 | 故障排查 |
| **系统** | 配置与概览 | ✅ 部分 | 新闻源配置 |

### 页面模块

**量化页**：运行参数/资金情况/做单情况/风控状态
**资讯页**：突发新闻/加密市场/金融市场/地缘政治
**宏观页**：宏观判断/一句话建议/国家统计局/宏观事件
**监控页**：巡检结果/告警信息/系统健康/故障排查
**系统页**：策略参数/新闻源/巡检配置/告警配置/数据概览

### 状态标签

- 正常：绿色
- 警告：黄色
- 异常：红色
- 无关键新闻：蓝色
- 接入中/筹备中：灰色
---

## 目录结构

```
~/openclaw-project/
├── scripts/              # 源码目录 (单源)
│   ├── grid_bot.py      # 网格机器人
│   ├── commander.py     # 主控汇总
│   ├── quant_report.py # 量化报告
│   ├── health_check.py # 健康巡检
│   └── demo_api_manager.py # Demo API 管理
├── runs/grid_bot/       # 运行目录 (符号链接)
│   └── bot.py -> ../scripts/grid_bot.py
├── data/latest/         # 状态文件
│   ├── commander_status.json
│   ├── quant_report.json
│   ├── news_report.json
│   └── macro_report.json
├── deploy/              # 部署脚本
│   ├── run_bot.sh
│   ├── restart_bot.sh
│   └── stop_bot.sh
└── logs/                # 日志目录
```

---

## 核心模块

### 量化交易系统

- **Binance Demo Trading** (binance_demo)
- **BTC/USDT**
- **Grid Bot**

执行模式：
- `binance_demo`：当前运行模式
- `binance_live`：未来实盘模式

### 状态协议

**核心文件**：`commander_status.json`

| 字段 | 说明 |
|------|------|
| overall_status | 总体状态 (ok/warning/degraded/critical) |
| quant.data_validity | 数据有效性 (true/false) |
| runtime.target_mode | 目标模式 |
| runtime.actual_mode | 实际模式 |
| runtime.degrade_reason | 降级原因 |

详见 [PROTOCOL.md](./PROTOCOL.md)

### Demo API 降级机制

当 Demo API 异常时：
1. 自动检测三条链 (market/account/order)
2. 连续 3 次失败触发熔断
3. 降级到 paper 模式
4. 禁止真实交易
5. 恢复后自动对账

---

## 已完成功能

- ✅ Binance Demo API 连接
- ✅ 获取余额/价格/挂单
- ✅ 挂单/撤单/查单
- ✅ 状态同步
- ✅ quant_report.json 生成
- ✅ commander_status.json 标准化
- ✅ Dashboard 状态显示
- ✅ Telegram 今日关注/巡检模板
- ✅ Demo API 降级与恢复
- ✅ 单源运行 (scripts/ 唯一源码)
- ✅ deploy 部署脚本
- ✅ 健康巡检脚本

---

## 快速开始

### 1. 克隆项目
```bash
git clone <你的仓库地址>
cd openclaw-project
```

### 2. 配置
```bash
# 复制配置
cp runs/grid_bot/.env.example runs/grid_bot/.env 2>/dev/null || true

# 编辑配置
vim runs/grid_bot/.env
```

必需配置：
```bash
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
EXECUTION_MODE=binance_demo
SYMBOL=BTC/USDT
```

### 3. 启动
```bash
# 方式1: 直接运行
cd runs/grid_bot
python3 bot.py &

# 方式2: 使用脚本
bash deploy/run_bot.sh
```

### 4. 验证
```bash
# 检查状态
cat data/latest/commander_status.json | python3 -m json.tool

# 查看今日关注
python3 scripts/commander.py "今天需要注意什么详细版"
```

---

## 状态查询

### Telegram 命令

| 命令 | 输出 |
|------|------|
| 今天需要注意什么详细版 | 今日关注详细版 |
| 系统状态 | 健康巡检 |
| 运行状态 | Bot 运行状态 |

### 关键指标

- **overall_status**: ok/warning/degraded/critical
- **data_validity**: true/false
- **freshness**: fresh/stale/expired/invalid

详见 [PROTOCOL.md](./PROTOCOL.md)

---

## 项目原则

1. **单源运行**：代码只有一份在 `scripts/`
2. **状态一致**：Telegram/Dashboard/JSON 共用同一套字段
3. **失败透明**：失败用 null，不用 0 伪装
4. **文档同步**：改代码后必须更新文档

---

## Roadmap

### Phase 1：Demo 验证 (当前)
- [x] Demo API 连接
- [x] 降级机制
- [x] 状态标准化
- [ ] 持续运行 1-2 个月验证

### Phase 2：内容运营 (规划)
- [ ] 小红书自动化
- [ ] 公众号内容
- [ ] 工程化/量化回测分享

### Phase 3：实盘评估
- [ ] 小资金实盘
- [ ] 风控增强

---

## 风险提示

- 本项目当前主要用于 Binance Demo Trading 验证
- 本仓库内容不构成任何投资建议
- 在未完成长期稳定性验证前，不建议直接用于实盘

---

## 相关文档

- [PROTOCOL.md](./PROTOCOL.md) - 状态协议标准
- [RUN_GUIDE.md](./RUN_GUIDE.md) - 运行指南
