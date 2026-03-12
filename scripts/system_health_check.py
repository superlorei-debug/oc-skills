#!/usr/bin/env python3
"""
系统健康检查脚本
检查各模块运行状态，生成健康报告
"""
import os
import json
import subprocess
from datetime import datetime, timedelta

PROJECT_DIR = "/Users/mac/.openclaw/workspace/openclaw-project"
DATA_DIR = f"{PROJECT_DIR}/data/latest"

def check_quant_process():
    """检查 Quant 策略进程"""
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            timeout=5
        )
        for line in result.stdout.split("\n"):
            # 检测网格机器人进程 (PID 36933)
            if "36933" in line or ("bot.py" in line and "Python" in line and "grid" in line.lower()):
                return {"status": "running", "detail": "网格机器人运行中 (PID 36933)"}
        return {"status": "stopped", "detail": "未检测到运行中的网格策略"}
    except Exception as e:
        return {"status": "unknown", "detail": str(e)}

def check_json_update():
    """检查 JSON 数据是否更新"""
    results = {}
    files = [
        "commander_summary.json",
        "quant_report.json", 
        "news_report.json",
        "macro_report.json"
    ]
    
    for fname in files:
        fpath = os.path.join(DATA_DIR, fname)
        if not os.path.exists(fpath):
            results[fname] = {"status": "missing", "detail": "文件不存在"}
            continue
        
        try:
            mtime = os.path.getmtime(fpath)
            file_time = datetime.fromtimestamp(mtime)
            now = datetime.now()
            age_minutes = (now - file_time).total_seconds() / 60
            
            if age_minutes < 30:
                results[fname] = {"status": "ok", "detail": f"更新于 {age_minutes:.1f} 分钟前"}
            elif age_minutes < 60:
                results[fname] = {"status": "warning", "detail": f"数据较旧 ({age_minutes:.0f} 分钟)"}
            else:
                results[fname] = {"status": "stale", "detail": f"数据过时 ({age_minutes:.0f} 分钟)"}
        except Exception as e:
            results[fname] = {"status": "error", "detail": str(e)}
    
    return results

def check_commander():
    """检查 Commander 汇总是否成功"""
    fpath = os.path.join(DATA_DIR, "commander_summary.json")
    if not os.path.exists(fpath):
        return {"status": "error", "detail": "汇总文件不存在"}
    
    try:
        with open(fpath) as f:
            data = json.load(f)
        
        required_fields = ["updated_at", "overall_risk_level", "overall_advice", "judgement_basis"]
        missing = [f for f in required_fields if f not in data]
        
        if missing:
            return {"status": "warning", "detail": f"缺少字段: {missing}"}
        
        return {"status": "ok", "detail": f"风险等级: {data.get('overall_risk_level', 'unknown')}"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

def check_dashboard():
    """检查 Dashboard 数据是否存在"""
    files = {
        "index.html": f"{PROJECT_DIR}/dashboard/index.html",
        "commander_summary.json": f"{DATA_DIR}/commander_summary.json",
        "quant_report.json": f"{DATA_DIR}/quant_report.json",
        "news_report.json": f"{DATA_DIR}/news_report.json",
        "macro_report.json": f"{DATA_DIR}/macro_report.json"
    }
    
    results = {}
    all_ok = True
    
    for name, path in files.items():
        if os.path.exists(path):
            results[name] = "exists"
        else:
            results[name] = "missing"
            all_ok = False
    
    if all_ok:
        return {"status": "ok", "detail": "所有必需文件存在"}
    else:
        return {"status": "error", "detail": f"缺少文件: {[k for k,v in results.items() if v == 'missing']}"}

def generate_report():
    """生成系统健康报告"""
    print("=" * 60)
    print("🔍 系统健康检查")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. Quant 策略
    print("1️⃣ Quant 策略")
    quant = check_quant_process()
    status_icon = "✅" if quant["status"] == "running" else "⚠️"
    print(f"   {status_icon} {quant['detail']}")
    print()
    
    # 2. JSON 数据
    print("2️⃣ JSON 数据更新状态")
    json_status = check_json_update()
    for fname, info in json_status.items():
        icon = "✅" if info["status"] == "ok" else ("⚠️" if info["status"] == "warning" else "❌")
        print(f"   {icon} {fname}: {info['detail']}")
    print()
    
    # 3. Commander
    print("3️⃣ Commander 汇总")
    commander = check_commander()
    icon = "✅" if commander["status"] == "ok" else "⚠️"
    print(f"   {icon} {commander['detail']}")
    print()
    
    # 4. Dashboard
    print("4️⃣ Dashboard 数据")
    dashboard = check_dashboard()
    icon = "✅" if dashboard["status"] == "ok" else "❌"
    print(f"   {icon} {dashboard['detail']}")
    print()
    
    # 总结
    print("=" * 60)
    
    # 计算健康度
    health_score = 0
    total_checks = 4
    
    if quant["status"] == "running":
        health_score += 1
    
    json_ok = sum(1 for i in json_status.values() if i["status"] == "ok")
    if json_ok >= 3:
        health_score += 1
    
    if commander["status"] == "ok":
        health_score += 1
    
    if dashboard["status"] == "ok":
        health_score += 1
    
    health_pct = int(health_score / total_checks * 100)
    
    if health_pct >= 75:
        overall = "✅ 健康"
    elif health_pct >= 50:
        overall = "⚠️ 警告"
    else:
        overall = "❌ 异常"
    
    print(f"系统健康度: {overall} ({health_pct}%)")
    print("=" * 60)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "quant": quant,
        "json": json_status,
        "commander": commander,
        "dashboard": dashboard,
        "health_score": health_score,
        "health_pct": health_pct
    }

def update_daily_report(health):
    """更新每日报告"""
    report_path = f"{PROJECT_DIR}/project_manager/daily_report.md"
    
    # 读取现有内容
    existing = ""
    if os.path.exists(report_path):
        with open(report_path) as f:
            existing = f.read()
    
    # 生成新内容
    quant_status = "✅ 正常" if health["quant"]["status"] == "running" else "⚠️ 异常"
    json_status = "✅ 正常" if health["json"]["quant_report.json"]["status"] == "ok" else "⚠️ 需关注"
    commander_status = "✅ 正常" if health["commander"]["status"] == "ok" else "⚠️ 需关注"
    dashboard_status = "✅ 正常" if health["dashboard"]["status"] == "ok" else "❌ 故障"
    
    new_entry = f"""## 日期: {datetime.now().strftime('%Y-%m-%d')}

### 系统状态

| 模块 | 状态 | 备注 |
|------|------|------|
| Quant | {quant_status} | {health['quant']['detail']} |
| JSON数据 | {json_status} | {health['json']['quant_report.json']['detail']} |
| Commander | {commander_status} | {health['commander']['detail']} |
| Dashboard | {dashboard_status} | {health['dashboard']['detail']} |

### 健康度: {health['health_pct']}%

---

"""
    
    # 保留模板，只替换内容
    if "## 日期: 2026-03-12" in existing:
        # 更新当天内容
        lines = existing.split("\n")
        new_lines = []
        skip_until_next = False
        for line in lines:
            if "## 日期:" in line and datetime.now().strftime('%Y-%m-%d') not in line:
                skip_until_next = True
            if not skip_until_next:
                new_lines.append(line)
            if "---" in line and skip_until_next:
                skip_until_next = False
        
        new_content = "\n".join(new_lines)
        new_content = new_content.replace("## 日期: 2026-03-12", new_entry.replace("---", "").strip())
    else:
        new_content = new_entry + "\n" + existing
    
    with open(report_path, "w") as f:
        f.write(new_content)
    
    print(f"\n📝 已更新: {report_path}")

if __name__ == "__main__":
    health = generate_report()
    update_daily_report(health)
