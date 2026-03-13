# 运行链标准说明

## 目录结构

### 主工程目录
```
~/openclaw-project/
├── scripts/           # 源码目录
│   ├── grid_bot.py   # 网格机器人
│   ├── commander.py  # 主控汇总
│   ├── quant_report.py # 量化报告
│   ├── health_check.py # 健康巡检
│   ├── telegram_alert.py # Telegram 告警
│   └── demo_api_manager.py # Demo API 管理
├── runs/            # 运行目录
│   └── grid_bot/    # 运行实例
│       ├── bot.py   # 符号链接 -> ../scripts/grid_bot.py
│       ├── .env    # 配置
│       └── state_v2.json  # 状态
├── data/
│   └── latest/     # 状态文件输出
│       ├── commander_status.json
│       ├── quant_report.json
│       ├── alert_state.json  # 告警状态
│       └── ...
├── deploy/          # 部署脚本
│   ├── run_bot.sh
│   ├── restart_bot.sh
│   └── stop_bot.sh
└── logs/           # 日志目录
```

## 统一路径定义

| 用途 | 路径 |
|------|------|
| **源码目录** | `~/openclaw-project/scripts/` |
| **运行目录** | `~/openclaw-project/runs/grid_bot/` |
| **状态文件** | `~/openclaw-project/data/latest/` |

---

## Dashboard 数据源

### 数据读取关系

| 组件 | 读取路径 | 数据真源 |
|------|----------|-----------|
| **Dashboard** | `../data/latest/*.json` | `data/latest/*.json` |
| commander.py | 直接写入 | data/latest/commander_status.json |
| quant_report.py | 直接写入 | data/latest/quant_report.json |

### 关键说明

- Dashboard 直接读取主真源 `data/latest/`
- 不再需要手工同步
- 每次 commander/quant_report 执行后，数据自动更新

### 故障排查

如果 Dashboard 显示 "-":

1. 先查主真源是否有数据：
```bash
cat ~/openclaw-project/data/latest/commander_status.json | python3 -m json.tool
```

2. 检查字段是否正确：
```bash
# 总体状态
grep overall_status ~/openclaw-project/data/latest/commander_status.json

# 量化数据
grep price_usd ~/openclaw-project/data/latest/quant_report.json
```

3. 如果主真源有数据但 Dashboard 显示 "-"，检查：
- Dashboard 服务是否运行
- 浏览器缓存

---

## Telegram 告警机制

### Dashboard 数据同步告警

当 Dashboard 数据异常时，系统会自动告警：

**触发条件：**
- commander_status.json 超过 5 分钟未更新
- quant_report.json 超过 5 分钟未更新
- news_report.json 超过 5 分钟未更新
- macro_report.json 超过 5 分钟未更新
- 任意关键文件不存在

**告警类型：**
- `dashboard_data_issue` - Dashboard 数据异常
- `dashboard_recovered` - Dashboard 数据恢复

**告警冷却：**
- 告警：1小时不重复
- 恢复：30分钟不重复

### 故障排查路径

| 问题 | 排查文件/命令 |
|------|---------------|
| Dashboard 显示 "-" | `data/latest/*.json` 是否存在/更新 |
| 告警没收到 | `alert_state.json` 冷却状态 |
| Telegram 发不出去 | `.env` TELEGRAM 配置 |
| **日志目录** | `~/openclaw-project/logs/` |

---

## 启动命令

### 1. Bot 启动
```bash
# 方式1: 直接运行
cd ~/openclaw-project/runs/grid_bot
python3 bot.py

# 方式2: 使用启动脚本
bash ~/openclaw-project/deploy/run_bot.sh
```

### 2. Telegram 告警检查
```bash
# 手动触发异常检查
python3 ~/openclaw-project/scripts/telegram_alert.py --check

# 测试告警消息
python3 ~/openclaw-project/scripts/telegram_alert.py --test-alert

# 测试恢复消息
python3 ~/openclaw-project/scripts/telegram_alert.py --test-recovery
```

---

## Telegram 消息机制

### 消息类型

| 类型 | 触发时间 | 说明 |
|------|----------|------|
| **巡检消息** | 每天 09:00 / 21:00 | 定时推送 |
| **异常告警** | 事件触发 | 异常发生时即时推送 |
| **恢复通知** | 事件触发 | 恢复正常后即时推送 |

### 巡检配置 (schedules.yaml)

```yaml
# 每天 09:00 早间巡检
- id: health-morning
  cron: "0 9 * * *"
  script: scripts/health_check.py

# 每天 21:00 晚间巡检
- id: health-evening
  cron: "0 21 * * *"
  script: scripts/health_check.py

# 每15分钟异常检查
- id: alert-check
  cron: "*/15 * * * *"
  script: scripts/telegram_alert.py
```

### 告警触发条件

| 场景 | 触发条件 |
|------|-----------|
| Bot 停止 | bot.running = false |
| Demo API 异常 | demo_api.connected = false |
| 系统降级 | actual_mode = paper |
| 禁止交易 | can_trade = false |
| 数据失效 | data_validity = false |

### 恢复触发条件

| 场景 | 触发条件 |
|------|-----------|
| Demo API 恢复 | demo_api.connected = true |
| 恢复交易 | can_trade = true |
| 退出降级 | actual_mode = binance_demo |
| 数据恢复 | data_validity = true |

### 去重/冷却机制

- 告警冷却：1小时内不重复告警
- 恢复冷却：30分钟内不重复通知

---

## 故障排查

### 排查路径

| 问题 | 排查文件 |
|------|----------|
| 定时巡检没发 | schedules.yaml 配置 |
| 异常没告警 | alert_state.json, telegram_alert.py |
| 告警发送失败 | Telegram Bot Token 配置 |
| 状态判断错误 | commander_status.json 字段 |

### 关键文件

| 文件 | 说明 |
|------|------|
| data/latest/commander_status.json | 核心状态文件 |
| data/latest/alert_state.json | 告警状态(冷却/去重) |
| data/latest/quant_report.json | 量化数据 |
| config/schedules.yaml | 定时任务配置 |

### 手工触发

```bash
# 手动触发告警检查
python3 scripts/telegram_alert.py --check

# 手动执行巡检
python3 scripts/health_check.py --type morning --send
python3 scripts/health_check.py --type evening --send

# 查看告警状态
cat data/latest/alert_state.json | python3 -m json.tool
```

---

## 更新发布流程

### 1. 开发测试
在 `scripts/` 目录修改代码

### 2. 提交 Git
```bash
cd ~/openclaw-project
git add scripts/
git commit -m "feat: ..."
git push
```

### 3. 同步到运行目录
```bash
# 复制源码
cp ~/openclaw-project/scripts/grid_bot.py ~/openclaw-project/runs/grid_bot/bot.py

# 重启 bot
pkill -f "bot.py"
cd ~/openclaw-project/runs/grid_bot
python3 bot.py &
```

### 4. 验证
```bash
# 检查进程
ps aux | grep bot.py

# 检查状态
cat ~/openclaw-project/data/latest/commander_status.json | python3 -m json.tool

# 检查告警状态
cat ~/openclaw-project/data/latest/alert_state.json | python3 -m json.tool
```

---

## 禁止事项

- ❌ 禁止直接从 `/tmp/binance-spot-grid-bot/` 运行
- ❌ 禁止在主工程目录外修改运行代码
- ❌ 禁止运行副本与仓库代码不同步
- ❌ 禁止跳过 schedules.yaml 直接改 cron

---

## 快速命令汇总

```bash
# 1. 启动 Bot
python3 runs/grid_bot/bot.py &

# 2. 重启
bash deploy/restart_bot.sh

# 3. 停止
bash deploy/stop_bot.sh

# 4. 查看状态
cat data/latest/commander_status.json | python3 -m json.tool

# 5. 手动告警检查
python3 scripts/telegram_alert.py --check

# 6. 测试告警消息
python3 scripts/telegram_alert.py --test-alert

# 7. 测试恢复消息
python3 scripts/telegram_alert.py --test-recovery

# 8. 手动巡检
python3 scripts/health_check.py --type morning --send
python3 scripts/health_check.py --type evening --send
```
