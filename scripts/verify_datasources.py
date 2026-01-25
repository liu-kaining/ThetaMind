#!/usr/bin/env python3
"""
数据源验证脚本
必须在 Day 1 开始时运行，验证所有依赖的数据源是否可用

Usage:
    python scripts/verify_datasources.py
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))

from app.services.market_data_service import MarketDataService
from app.services.tiger_service import tiger_service
from app.core.config import settings
from financetoolkit import Toolkit

# 颜色输出
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_status(message: str, status: str = "INFO"):
    """打印状态信息"""
    if status == "PASS":
        print(f"{Colors.GREEN}✅{Colors.RESET} {message}")
    elif status == "FAIL":
        print(f"{Colors.RED}❌{Colors.RESET} {message}")
    elif status == "WARN":
        print(f"{Colors.YELLOW}⚠️ {Colors.RESET} {message}")
    else:
        print(f"🔍 {message}")


async def verify_fmp_earnings_calendar() -> bool:
    """验证 FMP Earnings Calendar 接口"""
    print_status("Verifying FMP Earnings Calendar...")
    try:
        service = MarketDataService()
        
        # 获取未来 5 天的数据
        end_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        start_date = datetime.now().strftime("%Y-%m-%d")
        
        data = await service._call_fmp_api(
            "v3/earning_calendar",
            params={"from": start_date, "to": end_date}
        )
        
        if data and isinstance(data, list) and len(data) > 0:
            print_status(
                f"FMP Earnings Calendar: Available ({len(data)} earnings found)",
                "PASS"
            )
            return True
        else:
            print_status("FMP Earnings Calendar: No data returned", "WARN")
            return False
    except ValueError as e:
        if "API key" in str(e):
            print_status("FMP Earnings Calendar: API key not set", "FAIL")
            return False
        raise
    except Exception as e:
        print_status(f"FMP Earnings Calendar: Failed - {e}", "FAIL")
        return False


async def verify_fmp_unusual_activity() -> bool:
    """验证 FMP Unusual Activity 接口"""
    print_status("Verifying FMP Unusual Activity...")
    try:
        service = MarketDataService()
        
        # 尝试调用接口
        data = await service._call_fmp_api("stock/option-unusual-activity")
        
        if data and isinstance(data, (list, dict)):
            if isinstance(data, list) and len(data) > 0:
                print_status(
                    f"FMP Unusual Activity: Available ({len(data)} items)",
                    "PASS"
                )
            elif isinstance(data, dict):
                print_status("FMP Unusual Activity: Available (dict format)", "PASS")
            else:
                print_status("FMP Unusual Activity: Empty response", "WARN")
            return True
        else:
            print_status(
                "FMP Unusual Activity: No data returned (will use Plan B)",
                "WARN"
            )
            return False
    except ValueError as e:
        if "API key" in str(e):
            print_status("FMP Unusual Activity: API key not set", "WARN")
            return False
        raise
    except Exception as e:
        print_status(
            f"FMP Unusual Activity: Not available - {e} (will use Plan B)",
            "WARN"
        )
        return False


async def verify_financetoolkit_iv() -> bool:
    """验证 FinanceToolkit IV 计算"""
    print_status("Verifying FinanceToolkit IV calculation...")
    try:
        if not settings.financial_modeling_prep_key:
            print_status(
                "FinanceToolkit IV: FMP API key not set (will use HV as fallback)",
                "WARN"
            )
            return False
        
        # 测试股票：AAPL
        toolkit = Toolkit(
            ["AAPL"],
            api_key=settings.financial_modeling_prep_key
        )
        
        # 尝试获取 IV 数据
        iv_data = toolkit.options.get_implied_volatility()
        
        if iv_data is not None and not iv_data.empty:
            print_status(
                f"FinanceToolkit IV: Available (sample data: {len(iv_data)} rows)",
                "PASS"
            )
            return True
        else:
            print_status(
                "FinanceToolkit IV: No data returned (will use HV as fallback)",
                "WARN"
            )
            return False
    except Exception as e:
        print_status(
            f"FinanceToolkit IV: Failed - {e} (will use HV as fallback)",
            "WARN"
        )
        return False


async def verify_tiger_api() -> bool:
    """验证 Tiger API 连通性"""
    print_status("Verifying Tiger API connectivity...")
    try:
        available = await tiger_service.ping()
        if available:
            print_status("Tiger API: Available", "PASS")
            return True
        else:
            print_status("Tiger API: Not reachable", "WARN")
            return False
    except Exception as e:
        print_status(f"Tiger API: Failed - {e}", "WARN")
        return False


async def verify_financedatabase() -> bool:
    """验证 FinanceDatabase（本地库）"""
    print_status("Verifying FinanceDatabase (local library)...")
    try:
        import financedatabase as fd
        
        equities_db = fd.Equities()
        # 尝试搜索 SP500
        sp500 = equities_db.search(
            country="United States",
            market_cap="Large Cap"
        )
        
        if sp500 and len(sp500) > 0:
            print_status(
                f"FinanceDatabase: Available ({len(sp500)} US large cap stocks found)",
                "PASS"
            )
            return True
        else:
            print_status("FinanceDatabase: No data found", "WARN")
            return False
    except Exception as e:
        print_status(f"FinanceDatabase: Failed - {e}", "WARN")
        return False


async def main():
    """主验证流程"""
    print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}ThetaMind Data Source Verification{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print()
    
    results = {
        'fmp_earnings': await verify_fmp_earnings_calendar(),
        'fmp_unusual_activity': await verify_fmp_unusual_activity(),
        'financetoolkit_iv': await verify_financetoolkit_iv(),
        'financedatabase': await verify_financedatabase(),
        'tiger_api': await verify_tiger_api(),
    }
    
    print()
    print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}Verification Summary{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    
    for key, result in results.items():
        if result:
            status = f"{Colors.GREEN}✅ PASS{Colors.RESET}"
        else:
            status = f"{Colors.YELLOW}⚠️  FALLBACK / {Colors.RED}❌ FAIL{Colors.RESET}"
        print(f"{key:30} {status}")
    
    # 判断是否可以继续
    # 关键数据源：FMP Earnings 和 Tiger API
    critical = results['fmp_earnings'] and results['tiger_api']
    
    print()
    if not critical:
        print(f"{Colors.RED}{Colors.BOLD}⚠️  WARNING: Critical data sources are not available!{Colors.RESET}")
        print("   Please check your API keys and network connection.")
        print("   - FMP API key: Set FINANCIAL_MODELING_PREP_KEY in .env")
        print("   - Tiger API: Check TIGER_ID, TIGER_ACCOUNT, TIGER_PRIVATE_KEY")
        sys.exit(1)
    else:
        print(f"{Colors.GREEN}{Colors.BOLD}✅ All critical data sources are available. Proceeding...{Colors.RESET}")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
