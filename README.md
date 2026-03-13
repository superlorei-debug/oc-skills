# AI Quant Brain

基于 OpenClaw 的 AI 量化交易与信息分析工程项目。

当前核心运行主线为 **Binance Demo Trading 环境下的 BTC/USDT Grid Bot**。  
现阶段以 **稳定性验证** 为第一优先级，重点关注系统稳定运行、订单行为正确、状态同步准确，以及 Dashboard 与交易所数据一致。

---

## 当前状态

- **交易所**：Binance
- **运行模式**：Demo Trading
- **交易对**：BTC/USDT
- **策略类型**：Grid Bot
- **当前阶段**：Demo 验证阶段
- **验证周期**：1–2 个月

### 当前重点

- 系统稳定运行
- 订单行为正确
- 状态同步准确
- Dashboard 与交易所数据一致

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

## 核心模块

### 量化交易系统

当前主运行模块：

- **Binance Demo Trading**
- **BTC/USDT**
- **Grid Bot**

当前保留两种执行模式：

- `binance_demo`：当前运行模式
- `binance_live`：未来实盘模式

### AI 模块（规划中）

- quant-analyst
- news-geopolitics
- macro-advisor
- commander

### 信息系统（规划中）

未来将逐步接入：

- 国际新闻
- 宏观经济数据
- 中国经济统计数据

### Dashboard

Dashboard 当前已接入真实交易数据，后续将继续扩展展示：

- 量化交易数据
- 新闻分析
- 宏观分析
- 系统状态

---

## 已完成功能

当前已完成并进入验证阶段的能力包括：

- ✅ Binance API 连接
- ✅ 获取余额
- ✅ 获取价格
- ✅ 挂单
- ✅ 撤单
- ✅ 查询订单
- ✅ 状态同步
- ✅ quant_report.json 数据生成
- ✅ Dashboard 看板展示
- ✅ Demo 账户与看板数据同步

---

## 规划中功能

以下为后续扩展方向，当前不作为第一优先级：

- quant-analyst
- news-geopolitics
- macro-advisor
- commander
- 国际新闻接入与分析
- 宏观数据接入与分析
- 中国经济统计数据分析
- 综合分析报告生成
- 小资金实盘评估

---

## 项目结构

若 README 与实际仓库目录不一致，请以实际代码结构为准。

```
openclaw-project/
├── skills/
│   ├── commander/
│   ├── quant-analyst/
│   ├── news-geopolitics/
│   └── macro-advisor/
├── scripts/
│   ├── commander.py
│   ├── quant_report.py
│   ├── news_report.py
│   └── macro_report.py
├── config/
│   └── schedules.yaml
├── data/
├── logs/
├── deploy/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── deploy.sh
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 快速开始

### 环境要求

- Python 3.10+
- pip
- Binance API 凭证（当前建议优先使用 Demo 模式）

### 安装

```bash
git clone <你的仓库地址>
cd openclaw-project
pip install -r requirements.txt
```

### 配置

```bash
cp .env.example .env
```

编辑 `.env`，填写你的 API Key。

### 启动

```bash
python3 scripts/commander.py
```

---

## 环境变量

示例：

```bash
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
BINANCE_MODE=binance_demo
```

### 说明

- 当前阶段推荐使用 `BINANCE_MODE=binance_demo`
- `binance_live` 预留给未来实盘模式
- `.env` 不应提交到 Git

---

## 启动后验证清单

系统启动后，建议检查：

- [ ] Binance API 连接是否正常
- [ ] 账户余额是否拉取成功
- [ ] BTC/USDT 最新价格是否更新成功
- [ ] 挂单 / 撤单 / 查单行为是否正常
- [ ] 状态同步是否正常
- [ ] quant_report.json 是否生成成功
- [ ] Dashboard 是否显示最新交易数据
- [ ] Dashboard 数据是否与交易所一致

---

## 项目原则

- 优先保证系统稳定
- 交易所数据为真实来源
- 修改代码前必须先确认当前系统状态
- 所有改动都需要说明修改内容与验证结果
- 保持架构一致性，不随意推翻已有结构

---

## Roadmap

### Phase 1：Demo 验证

- [ ] 持续运行 1–2 个月
- [ ] 验证系统稳定性
- [ ] 验证订单行为
- [ ] 验证状态同步
- [ ] 验证 Dashboard 一致性

### Phase 2：AI 分析模块扩展

- [ ] quant-analyst
- [ ] news-geopolitics
- [ ] macro-advisor
- [ ] commander
- [ ] 新闻抓取与分析
- [ ] 宏观数据接入
- [ ] 经济统计分析

### Phase 3：小资金实盘评估

- [ ] 仅在 Demo 长期稳定后再考虑实盘
- [ ] 保留 binance_live 用于未来切换
- [ ] 实盘前优先补强监控、风控与验证机制

---

## 风险提示

- 本项目当前主要用于 Binance Demo Trading 验证
- 当前阶段重点是 **系统稳定性与数据一致性验证**
- 本仓库内容不构成任何投资建议
- 在未完成长期稳定性验证前，不建议直接用于实盘

---

## 仓库说明

- `data/` 为运行数据目录，通常不提交到 Git
- `logs/` 为运行日志目录，通常不提交到 Git
- `.env` 为本地私有配置，禁止提交到 Git
- README 应始终与实际仓库结构和运行状态保持一致

---

## 当前目标

持续稳定运行 Demo 系统，观察 1–2 个月，再考虑小资金实盘。
