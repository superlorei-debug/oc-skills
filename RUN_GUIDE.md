# 运行链标准说明

## 目录结构

### 主工程目录
```
~/openclaw-project/
├── scripts/           # 源码目录
│   ├── grid_bot.py   # 源码 (从 /tmp 同步)
│   ├── commander.py
│   ├── quant_report.py
│   └── demo_api_manager.py
├── runs/            # 运行目录
│   └── grid_bot/    # 运行实例
│       ├── bot.py   # 实际运行文件
│       ├── .env    # 配置
│       └── state_v2.json  # 状态
├── data/
│   └── latest/     # 状态文件输出
│       ├── commander_status.json
│       └── quant_report.json
└── logs/           # 日志目录
```

## 统一路径定义

| 用途 | 路径 |
|------|------|
| **源码目录** | `~/openclaw-project/scripts/` |
| **运行目录** | `~/openclaw-project/runs/grid_bot/` |
| **状态文件** | `~/openclaw-project/data/latest/` |
| **日志目录** | `~/openclaw-project/logs/` |

## 启动命令

### 方式1: 直接运行
```bash
cd ~/openclaw-project/runs/grid_bot
python3 bot.py
```

### 方式2: 使用启动脚本
```bash
cd ~/openclaw-project/runs/grid_bot
bash run.sh
```

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
pkill -f "grid_bot"  # 停止旧进程
cd ~/openclaw-project/runs/grid_bot
python3 bot.py &
```

### 4. 验证
```bash
# 检查进程
ps aux | grep bot.py

# 检查状态
cat ~/openclaw-project/data/latest/commander_status.json | python3 -m json.tool
```

## 禁止事项

- ❌ 禁止直接从 `/tmp/binance-spot-grid-bot/` 运行
- ❌ 禁止在主工程目录外修改运行代码
- ❌ 禁止运行副本与仓库代码不同步

## 快速命令汇总

```bash
# 1. 同步代码
cp ~/openclaw-project/scripts/grid_bot.py ~/openclaw-project/runs/grid_bot/bot.py

# 2. 重启
pkill -f "bot.py" 
cd ~/openclaw-project/runs/grid_bot && python3 bot.py &

# 3. 查看状态
cat ~/openclaw-project/data/latest/commander_status.json | python3 -m json.tool
```
