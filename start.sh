#!/bin/bash

echo "========================================="
echo "🦞 OpenClaw 财富管家"
echo "========================================="

# 1. 加载环境变量
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 2. 显示菜单
echo ""
echo "请选择操作："
echo "1. 查看今日总览"
echo "2. 查看量化状态"
echo "3. 查看新闻"
echo "4. 查看宏观理财"
echo "5. 退出"
echo ""

read -p "请输入选项 (1-5): " choice

case $choice in
    1)
        echo ""
        echo "📋 今日总览..."
        python3 scripts/commander.py
        ;;
    2)
        echo ""
        echo "📈 量化状态..."
        python3 scripts/quant_report.py
        ;;
    3)
        echo ""
        echo "📰 新闻..."
        python3 scripts/news_report.py
        ;;
    4)
        echo ""
        echo "📊 宏观理财..."
        python3 scripts/macro_report.py
        ;;
    5)
        echo "退出"
        exit 0
        ;;
    *)
        echo "无效选项"
        exit 1
        ;;
esac
