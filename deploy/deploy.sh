#!/bin/bash

set -e

echo "========================================="
echo "🚀 OpenClaw 财富管家部署脚本"
echo "========================================="

# 1. 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "❌ .env 文件不存在，正在创建..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 填写 API Keys"
    nano .env
fi

# 2. 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装"
    exit 1
fi

# 3. 检查 docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose 未安装"
    exit 1
fi

# 4. 构建并启动
echo "📦 正在构建 Docker 镜像..."
docker-compose build

echo "🚀 正在启动服务..."
docker-compose up -d

# 5. 检查状态
echo "📊 检查服务状态..."
sleep 3
docker-compose ps

echo ""
echo "========================================="
echo "✅ 部署完成！"
echo "========================================="
echo ""
echo "查看日志: docker-compose logs -f"
echo "停止服务: docker-compose down"
echo "重启服务: docker-compose restart"
