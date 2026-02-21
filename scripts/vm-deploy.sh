#!/bin/bash
# ThetaMind VM 部署脚本（适用于 Google Cloud VM / 任意 Linux VM）
# 使用前：在仓库根目录准备 .env，然后执行 ./scripts/vm-deploy.sh 或 bash scripts/vm-deploy.sh

set -e

# 确保在仓库根目录执行（支持从 repo 根目录或 scripts/ 下运行）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"
echo "工作目录: $ROOT_DIR"

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

# 检查 .env 文件（在仓库根目录）
if [ ! -f "$ROOT_DIR/.env" ]; then
    echo "警告: .env 文件不存在"
    if [ -f "$ROOT_DIR/.env.example" ]; then
        echo "从 .env.example 创建 .env 文件..."
        cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
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
set -a
# shellcheck source=/dev/null
source "$ROOT_DIR/.env"
set +a

# 注意：对于 docker-compose 环境，DATABASE_URL 会自动从 DB_USER、DB_PASSWORD、DB_NAME 构建
# 所以只需要检查 DB_PASSWORD 即可（DB_USER 和 DB_NAME 有默认值）
REQUIRED_VARS=(
    "DB_PASSWORD"  # 数据库密码（必需，docker-compose 会自动构建 DATABASE_URL）
    "JWT_SECRET_KEY"
    "GOOGLE_CLIENT_ID"
    "GOOGLE_CLIENT_SECRET"
    "GOOGLE_API_KEY"
)

# 可选变量，如果没有设置会给出提示，但不报错中断
OPTIONAL_VARS=(
    "GOOGLE_VERTEX_API_KEY"
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

for var in "${OPTIONAL_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "提示: ${var} 未设置"
    fi
done

# 可选：FMP 未配置时行情/基本面不可用（AI 仍可用）
if [ -z "${FINANCIAL_MODELING_PREP_KEY:-}" ]; then
    echo "提示: FINANCIAL_MODELING_PREP_KEY 未设置，行情/基本面数据将不可用"
fi

echo "环境变量检查通过"

# 停止现有容器（如果存在）
echo "停止现有容器..."
docker compose down 2>/dev/null || true

# 构建并启动服务（共 5 个：db, redis, backend, frontend, nginx）
echo "构建并启动服务（含 Nginx，监听 80 端口）..."
docker compose up -d --build

# 等待服务启动（DB/Redis 健康检查通过后 backend 才能就绪）
echo "等待服务启动..."
sleep 10

# 显式执行数据库迁移（one-off 容器：只跑 alembic 后退出；主 backend 容器启动时 entrypoint 也会跑一次迁移）
echo "运行数据库迁移..."
docker compose run --rm backend alembic upgrade head || {
    echo "错误: 数据库迁移失败，请检查上方日志（如 DATABASE_URL、网络等）"
    exit 1
}

# 确保 Nginx 也启动（若因依赖顺序未启动则补拉）
echo "确保 Nginx 已启动..."
docker compose up -d nginx 2>/dev/null || true

sleep 3

# 检查服务状态（含已退出的容器，便于发现 nginx 是否启动失败）
echo "检查服务状态（预期 5 个容器：db, redis, backend, frontend, nginx）..."
docker compose ps -a

# 诊断：80 能访问的前提是「本机有进程监听 80」。只有 Nginx 容器在跑时才会监听 80。
LISTEN_80=$(ss -tlnp 2>/dev/null | grep -E ':80\s' || netstat -tlnp 2>/dev/null | grep -E ':80\s' || true)
NGINX_RUNNING=$(docker compose ps --status running --format "{{.Name}}" 2>/dev/null | grep -E 'nginx|thetamind-nginx' || true)

if [ -z "$NGINX_RUNNING" ]; then
    echo ""
    echo ">>> 当前 80 端口不可用的原因：Nginx 容器未运行，本机没有进程监听 80。"
    echo "    防火墙放行 80 只表示允许流量进 VM；若无人监听 80，外网访问仍会失败。"
    echo ">>> 请在本机执行以下命令排查并启动 Nginx："
    echo "    docker compose logs nginx    # 查看 Nginx 为何未启动或退出"
    echo "    docker compose up -d nginx   # 再次尝试启动 Nginx"
    echo "    ss -tlnp | grep 80           # 启动成功后应能看到 0.0.0.0:80"
    echo ""
elif [ -z "$LISTEN_80" ]; then
    echo ""
    echo ">>> Nginx 容器在运行，但本机未检测到 80 端口监听。请执行: ss -tlnp | grep 80"
    echo ""
fi

echo ""
echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo "服务状态："
docker compose ps -a
echo ""
if [ -n "$NGINX_RUNNING" ] && [ -n "$LISTEN_80" ]; then
    echo "【80 已就绪】通过 Nginx 访问: http://localhost 或 http://$(hostname -I 2>/dev/null | awk '{print $1}')"
else
    echo "【推荐】通过 80 端口访问（需 Nginx 运行）: http://localhost 或 http://$(hostname -I 2>/dev/null | awk '{print $1}')"
    echo "若 80 暂不可用，可临时访问："
    echo "  前端: http://localhost:3000  后端: http://localhost:5300"
fi
echo ""
echo "常用命令："
echo "  查看日志: docker compose logs -f    Nginx 日志: docker compose logs nginx"
echo "  停止服务: docker compose down      重启服务: docker compose restart"
echo ""
echo "同步本地股票 symbol 表（可选，非每次部署必做）："
echo "  ./scripts/sync-symbols-on-vm.sh     # 或: docker compose run --rm backend python scripts/sync_symbols_from_fmp.py --us-only"
echo "  说明: 需服务器能访问 FMP；建议首次部署或定期（如每周）跑一次，Strategy Lab / Company Data 搜索会更全。"
echo ""
echo "Google Cloud: 防火墙已放行 80 后，若仍无法访问，请确认 VM 上有进程监听 80（即 Nginx 已启动）。"
echo ""
