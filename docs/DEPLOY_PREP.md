# AI Quant Brain 服务器上线前准备清单

> **版本**: v1.0  
> **创建日期**: 2026-03-15  
> **当前阶段**: 稳定观察期 → 上线准备

---

## 一、当前阶段划分

### 阶段 1：稳定观察期（当前）
- **状态**: 正在运行
- **目标**: 验证系统稳定性
- **禁止**: 大规模服务器改造

### 阶段 2：上线准备期（观察结束后）
- **分支**: 从 master 拉出 `release/prod-prep`
- **目标**: 准备服务器部署环境

### 阶段 3：正式部署
- **来源**: master 分支验证后合并到 release/prod-prep
- **目标**: 部署到生产服务器

---

## 二、当前基座评估

### 2.1 master 是否具备部署条件

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 量化主链 | ✅ 可用 | Grid Bot 正常运行 |
| Dashboard | ✅ 可用 | V2 完成，5 菜单 |
| Telegram 巡检 | ✅ 可用 | 定时发送 |
| Telegram 告警 | ✅ 可用 | 异常告警 |
| freshness 分层 | ✅ 统一 | 检查层与告警层一致 |
| 分支规划 | ✅ 完成 | BRANCH_STRATEGY.md |

### 2.2 还缺什么

| 缺口项 | 说明 | 优先级 |
|--------|------|--------|
| 服务器环境 | 需要一台 Linux 服务器 | P0 |
| 生产 secrets 管理 | 分离 .env 到运行目录外 | P0 |
| 进程守护 | systemd/supervisor 配置 | P0 |
| 反向代理 | Nginx/Caddy 配置 | P1 |
| 域名 | 购买并绑定 | P1 |
| HTTPS | Let's Encrypt | P1 |
| 日志持久化 | 日志文件持久化方案 | P2 |
| 备份机制 | 数据备份脚本 | P2 |

---

## 三、上线准备清单

### 3.1 观察期内暂不动的内容

| 项目 | 原因 |
|------|------|
| 交易执行逻辑 | 保持稳定观察 |
| Dashboard 业务结构 | 已固定 |
| 宏观数据接入 | 方案已设计，暂不落生产 |
| 自我进化实验 | 隔离在 exp/evolution-v1 |

### 3.2 观察期结束后、上线前必须准备

| 序号 | 项目 | 说明 |
|------|------|------|
| 1 | 创建 release/prod-prep 分支 | 从 master 拉出 |
| 2 | 服务器采购 | Linux 服务器 (Ubuntu 20.04+) |
| 3 | Python 环境统一 | 3.11+ |
| 4 | 依赖安装 | requests, dotenv 等 |
| 5 | secrets 分离 | .env 放到运行目录外 |
| 6 | 进程守护配置 | systemd service 文件 |
| 7 | Dashboard 启动配置 | HTTP 服务器 |
| 8 | 定时任务配置 | scheduler 或 systemd timer |
| 9 | 日志配置 | 日志轮转 |
| 10 | 数据持久化 | data/ 目录 |

### 3.3 上线当天执行内容

| 序号 | 项目 | 说明 |
|------|------|------|
| 1 | 拉取 release/prod-prep 分支 | git pull |
| 2 | 配置 .env | 生产 API keys |
| 3 | 安装依赖 | pip install -r requirements.txt |
| 4 | 启动 Grid Bot | nohup 或 systemd |
| 5 | 启动 Dashboard | python -m http.server 8080 |
| 6 | 启动 scheduler | 后台运行 health_check |
| 7 | 验证 Telegram 巡检 | 手动触发 |
| 8 | 验证 Dashboard 访问 | curl localhost:8080 |

---

## 四、release/prod-prep 分支准备内容

### 4.1 应在此分支准备的内容

| 项目 | 说明 |
|------|------|
| systemd service 文件 | grid_bot.service, scheduler.service |
| Nginx 配置 | 反向代理 + HTTPS |
| .env 生产模板 | 生产环境变量示例 |
| 启动脚本 | start_prod.sh |
| 日志配置 | logrotate 配置 |
| 备份脚本 | backup_data.sh |
| 部署文档 | deploy_guide.md |

### 4.2 不应在此分支修改的内容

| 项目 | 原因 |
|------|------|
| scripts/grid_bot.py | 保持 master 同步 |
| scripts/health_check.py | 保持 master 同步 |
| scripts/telegram_alert.py | 保持 master 同步 |
| Dashboard 业务逻辑 | 保持稳定 |

---

## 五、服务器环境建议

### 5.1 操作系统
- **推荐**: Ubuntu 20.04 LTS 或 22.04 LTS
- **最低**: Ubuntu 18.04

### 5.2 Python 环境
- **版本**: Python 3.11+
- **依赖**: 
  - requests
  - python-dotenv
  - numpy (如需要)

### 5.3 目录结构（服务器）

```
/home/user/ai-quant-brain/
├── scripts/           # 从仓库克隆
├── data/
│   ├── latest/       # 状态文件
│   └── evolution/    # 进化数据
├── logs/             # 日志目录
├── runs/
│   └── grid_bot/
│       └── .env     # 生产 secrets (不放仓库)
└── dashboard/        # Dashboard
```

### 5.4 进程守护方式

推荐使用 **systemd**:

```ini
# /etc/systemd/system/grid-bot.service
[Unit]
Description=AI Quant Brain Grid Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/user/ai-quant-brain
ExecStart=/usr/bin/python3 scripts/grid_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## 六、最小正式环境方案

### 6.1 目标
先做到：可用 + 可看 + 可监控

### 6.2 组件

| 组件 | 用途 | 启动方式 |
|------|------|----------|
| Grid Bot | 交易执行 | systemd |
| Dashboard | 数据展示 | python -m http.server |
| scheduler | 定时巡检 | systemd timer |
| health_check | 健康检查 | 定时任务 |
| telegram_alert | 告警推送 | 定时任务 |

### 6.3 最小启动命令

```bash
# Grid Bot
nohup python3 scripts/grid_bot.py > logs/grid_bot.log 2>&1 &

# Dashboard
cd dashboard && nohup python3 -m http.server 8080 > logs/dashboard.log 2>&1 &

# Scheduler
nohup python3 scripts/scheduler.py > logs/scheduler.log 2>&1 &
```

---

## 七、上线步骤

### 7.1 上线前检查

- [ ] 观察期结束确认
- [ ] master 分支最新
- [ ] release/prod-prep 分支已创建
- [ ] 服务器环境准备完成
- [ ] 生产 .env 已配置
- [ ] 依赖已安装

### 7.2 上线当天执行顺序

```
1. git clone / git pull release/prod-prep
2. 配置生产 .env
3. 安装依赖 (pip install -r requirements.txt)
4. 启动 Grid Bot (验证能连 Demo API)
5. 启动 Dashboard (验证能访问)
6. 启动 scheduler (验证定时任务)
7. 手动触发 health_check (验证 Telegram)
8. 检查 Dashboard 数据刷新
```

### 7.3 上线后验证清单

| 验证项 | 检查方式 |
|--------|----------|
| Grid Bot 运行 | ps aux \| grep grid_bot |
| Dashboard 访问 | curl localhost:8080 |
| Telegram 巡检 | 手动触发 health_check |
| 数据刷新 | 查看 data/latest/ 文件时间 |
| 挂单正常 | quant_report.json |

---

## 八、回滚建议

### 8.1 回滚场景

| 场景 | 回滚方式 |
|------|----------|
| Grid Bot 异常 | systemctl stop grid-bot, 检查日志 |
| Dashboard 异常 | 重启 HTTP 服务 |
| 全部异常 | 回滚到上一个稳定版本 |

### 8.2 回滚命令

```bash
# 停止所有服务
systemctl stop grid-bot
systemctl stop dashboard

# 回滚代码
git checkout <last-stable-commit>

# 重启
systemctl start grid-bot
```

---

## 九、当前评估结论

### 9.1 当前是否具备上线准备基础

**当前 master 已具备未来部署基座条件；待稳定观察期完成后，再从 master 拉出 release/prod-prep 进入服务器上线准备阶段。**

| 检查项 | 状态 |
|--------|------|
| 量化主链 | ✅ 可用 |
| Dashboard | ✅ 可用 |
| Telegram 巡检 | ✅ 可用 |
| Telegram 告警 | ✅ 可用 |
| freshness 分层 | ✅ 统一 |
| 分支规划 | ✅ 完成 |
| 服务器环境 | ⚠️ 待准备 |

### 9.2 下一步建议

1. **继续观察**: 保持当前稳定观察 (7 天)
2. **观察结束后**: 创建 release/prod-prep 分支
3. **服务器准备**: 采购 Linux 服务器
4. **环境配置**: 按本清单准备

---

## 十、相关文档

- [BRANCH_STRATEGY.md](./BRANCH_STRATEGY.md) - 分支协作规则
- [OBSERVATION_BASELINE.md](./OBSERVATION_BASELINE.md) - 稳定观察期基线
- [RUN_GUIDE.md](./RUN_GUIDE.md) - 运行链说明
- [PROTOCOL.md](./PROTOCOL.md) - 状态协议

---

*本文档为服务器上线前准备清单，观察期结束后按此执行。*
