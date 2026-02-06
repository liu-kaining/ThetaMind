"""
获取一份期权链数据并保存为开发环境测试数据（option_chain_fixture.json）。

开发/生产会抢占 Tiger 期权接口，开发环境应使用 TIGER_USE_LIVE_API=false 并加载此 fixture，
不直接调用线上服务。生产环境保持 TIGER_USE_LIVE_API=true。

使用方法:
  1. 在能调用 Tiger 的环境下（生产或临时开 live）执行一次:
     TIGER_USE_LIVE_API=true docker-compose exec backend python scripts/save_option_chain_fixture.py
     或: TIGER_USE_LIVE_API=true python scripts/save_option_chain_fixture.py  # 在 backend 目录下
  2. 将生成的 app/data/fixtures/option_chain_fixture.json 提交或拷贝到开发机
  3. 开发环境 .env 中设置 TIGER_USE_LIVE_API=false，即可使用测试数据，不抢占线上
"""
import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

script_dir = Path(__file__).parent
backend_dir = script_dir.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.services.tiger_service import tiger_service, _get_option_chain_fixture_path


async def main(symbol: str = "AAPL") -> None:
    if not settings.tiger_use_live_api:
        print("⚠️  TIGER_USE_LIVE_API 当前为 false，无法调用 Tiger 获取真实数据。")
        print("   请先设置 TIGER_USE_LIVE_API=true 再运行本脚本。")
        sys.exit(1)

    if not tiger_service._client:
        print("❌ TigerService 未初始化，请检查 Tiger 配置（TIGER_ID、私钥等）。")
        sys.exit(1)

    # 取一个近期到期日
    today = datetime.now()
    days_until_friday = (4 - today.weekday() + 7) % 7 or 7
    next_friday = today + timedelta(days=days_until_friday)
    expiration_date = next_friday.strftime("%Y-%m-%d")

    print(f"正在从 Tiger 获取期权链: symbol={symbol}, expiration={expiration_date}")
    try:
        chain_data = await tiger_service.get_option_chain(
            symbol=symbol.upper(),
            expiration_date=expiration_date,
            is_pro=False,
            force_refresh=True,
        )
    except Exception as e:
        print(f"❌ 获取期权链失败: {e}")
        sys.exit(1)

    try:
        expirations = await tiger_service.get_option_expirations(symbol.upper())
    except Exception as e:
        print(f"⚠️  获取到期日列表失败，使用默认: {e}")
        expirations = [expiration_date]

    # 组装与 fixture 格式一致的结构
    option_chain = {
        "calls": chain_data.get("calls") or [],
        "puts": chain_data.get("puts") or [],
        "spot_price": chain_data.get("spot_price") or chain_data.get("underlying_price"),
    }
    payload = {
        "option_chain": option_chain,
        "expirations": expirations,
    }

    out_path = _get_option_chain_fixture_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str, ensure_ascii=False)

    print(f"✅ 已保存到: {out_path}")
    print(f"   calls: {len(option_chain['calls'])}, puts: {len(option_chain['puts'])}, expirations: {len(expirations)}")


if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    asyncio.run(main(symbol=symbol))
