#!/bin/bash
# 在 VM/服务器上同步 FMP 股票 symbol 到本地 DB（可选，非每次部署必跑）
# 使用：在仓库根目录执行 ./scripts/sync-symbols-on-vm.sh
# 建议：首次部署后跑一次，或 cron 每周跑（例如 0 3 * * 0 周日 3 点）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f "$ROOT_DIR/.env" ]; then
    echo "错误: .env 不存在，请先在仓库根目录配置 .env"
    exit 1
fi

set -a
# shellcheck source=/dev/null
source "$ROOT_DIR/.env"
set +a

if [ -z "${FINANCIAL_MODELING_PREP_KEY:-}" ]; then
    echo "错误: .env 中未设置 FINANCIAL_MODELING_PREP_KEY，无法调用 FMP。"
    exit 1
fi

echo "正在从 FMP 同步 symbol 到本地 DB（--us-only）..."
docker compose run --rm backend python scripts/sync_symbols_from_fmp.py --us-only

echo "完成。Strategy Lab / Company Data 搜索将使用更新后的 symbol 表。"
