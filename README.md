# 🦞 OpenClaw 财富管家

> 基于 OpenClaw 的量化交易、新闻分析、宏观决策助手

## 功能模块

| 模块 | 功能 |
|------|------|
| Commander | 主控汇总，统一入口 |
| Quant Analyst | 量化策略监控与分析 |
| News Geopolitics | 新闻与地缘政治影响 |
| Macro Advisor | 宏观与家庭理财建议 |

## 项目结构

```
openclaw-project/
├── skills/                  # 核心模块
│   ├── commander/       # 主控汇总
│   ├── quant-analyst/   # 量化分析
│   ├── news-geopolitics/ # 新闻地缘
│   └── macro-advisor/   # 宏观理财
├── scripts/                  # 可执行脚本
│   ├── commander.py     # 今日总览
│   ├── quant_report.py   # 量化状态
│   ├── news_report.py   # 新闻分析
│   └── macro_report.py  # 宏观理财
├── config/                   # 配置文件
│   └── schedules.yaml    # 定时任务配置
├── data/                    # 运行数据（不提交Git）
│   ├── history/          # 历史记录
│   ├── cache/           # 缓存
│   └── push_logs/       # 推送记录
├── logs/                    # 日志（不提交Git）
├── deploy/                   # 部署脚本
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── deploy.sh
├── .env.example             # 环境变量模板
├── .gitignore              # Git忽略配置
├── requirements.txt        # Python依赖
└── README.md
```

## 快速开始

### 本地启动

```bash
# 1. 克隆项目
git clone <你的仓库地址>
cd openclaw-project

# 2. 复制配置
cp .env.example .env
nano .env  # 编辑你的 API Keys

# 3. 运行
python3 scripts/commander.py
```

### 查看各模块

```bash
# 今日总览
python3 scripts/commander.py

# 量化状态
python3 scripts/quant_report.py

# 新闻分析
python3 scripts/news_report.py

# 宏观理财
python3 scripts/macro_report.py
```

## 云服务器部署

```bash
# 1. 克隆
git clone <你的仓库地址>
cd openclaw-project

# 2. 配置
cp .env.example .env
nano .env

# 3. 一键部署
bash deploy/deploy.sh
```

## 配置说明

### 环境变量 (.env)

```
# 币安交易
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret

# 可选模型
QWEN_API_KEY=your_qwen_key
GLM_API_KEY=your_glm_key
```

### 定时任务 (config/schedules.yaml)

| 任务 | 默认时间 |
|------|----------|
| 新闻推送 | 9:00 |
| 量化汇报 | 21:00 |
| 小红书 | 周三/周日 21:00 |

## 目录说明

| 目录 | 用途 | 提交到Git |
|------|------|----------|
| skills/ | 模块代码 | ✅ |
| scripts/ | 执行脚本 | ✅ |
| config/ | 配置文件 | ✅ |
| deploy/ | 部署脚本 | ✅ |
| data/ | 运行数据 | ❌ |
| logs/ | 日志 | ❌ |

## License

MIT
