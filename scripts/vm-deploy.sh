#!/bin/bash
# 简单的 VM 部署脚本
# 用于在 VM 上快速部署 ThetaMind

set -e

echo "=========================================="
echo "ThetaMind VM 部署脚本"
echo "=========================================="

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "Docker 未安装，正在安装..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "Docker 安装完成，请重新登录或运行: newgrp docker"
    exit 0
fi

# 检查 Docker Compose 是否安装
if ! command -v docker compose &> /dev/null; then
    echo "Docker Compose 未安装，正在安装..."
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
fi

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "警告: .env 文件不存在"
    if [ -f .env.example ]; then
        echo "从 .env.example 创建 .env 文件..."
        cp .env.example .env
        echo "请编辑 .env 文件，填入所有必需的配置"
        echo "然后重新运行此脚本"
        exit 1
    else
        echo "错误: .env.example 文件也不存在"
        exit 1
    fi
fi

# 检查必要的环境变量
echo "检查环境变量配置..."
source .env

# 注意：对于 docker-compose 环境，DATABASE_URL 会自动从 DB_USER、DB_PASSWORD、DB_NAME 构建
# 所以只需要检查 DB_PASSWORD 即可（DB_USER 和 DB_NAME 有默认值）
REQUIRED_VARS=(
    "DB_PASSWORD"  # 数据库密码（必需，docker-compose 会自动构建 DATABASE_URL）
    "JWT_SECRET_KEY"
    "GOOGLE_CLIENT_ID"
    "GOOGLE_CLIENT_SECRET"
    "GOOGLE_API_KEY"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo "错误: 以下必需的环境变量未设置:"
    printf '%s\n' "${MISSING_VARS[@]}"
    echo "请编辑 .env 文件并设置这些变量"
    exit 1
fi

echo "环境变量检查通过"

# 停止现有容器（如果存在）
echo "停止现有容器..."
docker compose down 2>/dev/null || true

# 构建并启动服务
echo "构建并启动服务..."
docker compose up -d --build

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 检查服务状态
echo "检查服务状态..."
docker compose ps

# 显示日志
echo ""
echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo "服务状态："
docker compose ps
echo ""
echo "查看日志: docker compose logs -f"
echo "停止服务: docker compose down"
echo "重启服务: docker compose restart"
echo ""
echo "前端地址: http://localhost:3000"
echo "后端地址: http://localhost:5300"
echo "API 文档: http://localhost:5300/docs"
echo ""

