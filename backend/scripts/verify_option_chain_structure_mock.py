"""
验证期权链数据结构 - 使用模拟数据演示期望的结构

这个脚本展示了我们期望的期权链数据结构，即使没有权限也可以运行。

使用方法:
    docker-compose exec backend python scripts/verify_option_chain_structure_mock.py
"""
import json
from datetime import datetime, timedelta


def print_section(title: str):
    """打印分节标题"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def print_json(data, indent=2):
    """安全打印 JSON 数据"""
    try:
        return json.dumps(data, indent=indent, default=str, ensure_ascii=False)
    except Exception as e:
        return str(data)


def create_mock_option_chain(symbol: str = "AAPL", spot_price: float = 150.0):
    """创建模拟的期权链数据，展示我们期望的结构"""
    
    # 计算到期日期
    expiration_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    # 模拟期权链数据
    mock_chain = {
        # 关键：标的股票价格
        "spot_price": spot_price,  # 或者可能是 "underlying_price"
        "underlying_price": spot_price,  # 备选字段名
        
        # 到期日期
        "expiration_date": expiration_date,
        
        # Calls 数组
        "calls": [
            {
                # 执行价
                "strike": 145.0,
                "strike_price": 145.0,  # 备选字段名
                
                # 价格
                "bid": 8.5,
                "ask": 8.7,
                "bid_price": 8.5,  # 备选字段名
                "ask_price": 8.7,  # 备选字段名
                "last_price": 8.6,
                
                # 交易量
                "volume": 1250,
                "open_interest": 5000,
                
                # Greeks - 方式1: 直接字段
                "delta": 0.65,
                "gamma": 0.02,
                "theta": -0.15,
                "vega": 0.25,
                "rho": 0.03,
                
                # Greeks - 方式2: 嵌套对象（我们的代码也支持）
                "greeks": {
                    "delta": 0.65,
                    "gamma": 0.02,
                    "theta": -0.15,
                    "vega": 0.25,
                    "rho": 0.03,
                },
                
                # 隐含波动率
                "implied_volatility": 0.25,
                "iv": 0.25,
                
                # 其他信息
                "contract_id": "AAPL240119C00145000",
                "expiration": expiration_date,
                "days_to_expiration": 30,
            },
            {
                "strike": 150.0,
                "bid": 5.0,
                "ask": 5.2,
                "delta": 0.50,
                "gamma": 0.025,
                "theta": -0.18,
                "vega": 0.30,
                "rho": 0.04,
                "greeks": {
                    "delta": 0.50,
                    "gamma": 0.025,
                    "theta": -0.18,
                    "vega": 0.30,
                    "rho": 0.04,
                },
                "volume": 2500,
                "open_interest": 8000,
                "implied_volatility": 0.24,
            },
            {
                "strike": 155.0,
                "bid": 2.5,
                "ask": 2.7,
                "delta": 0.30,
                "gamma": 0.02,
                "theta": -0.12,
                "vega": 0.20,
                "rho": 0.02,
                "greeks": {
                    "delta": 0.30,
                    "gamma": 0.02,
                    "theta": -0.12,
                    "vega": 0.20,
                    "rho": 0.02,
                },
                "volume": 1800,
                "open_interest": 6000,
                "implied_volatility": 0.23,
            },
        ],
        
        # Puts 数组（类似结构）
        "puts": [
            {
                "strike": 145.0,
                "bid": 2.0,
                "ask": 2.2,
                "delta": -0.35,
                "gamma": 0.02,
                "theta": -0.15,
                "vega": 0.25,
                "rho": -0.03,
                "greeks": {
                    "delta": -0.35,
                    "gamma": 0.02,
                    "theta": -0.15,
                    "vega": 0.25,
                    "rho": -0.03,
                },
                "volume": 800,
                "open_interest": 4000,
                "implied_volatility": 0.25,
            },
            {
                "strike": 150.0,
                "bid": 5.0,
                "ask": 5.2,
                "delta": -0.50,
                "gamma": 0.025,
                "theta": -0.18,
                "vega": 0.30,
                "rho": -0.04,
                "greeks": {
                    "delta": -0.50,
                    "gamma": 0.025,
                    "theta": -0.18,
                    "vega": 0.30,
                    "rho": -0.04,
                },
                "volume": 2200,
                "open_interest": 7500,
                "implied_volatility": 0.24,
            },
            {
                "strike": 155.0,
                "bid": 8.5,
                "ask": 8.7,
                "delta": -0.70,
                "gamma": 0.02,
                "theta": -0.12,
                "vega": 0.20,
                "rho": -0.02,
                "greeks": {
                    "delta": -0.70,
                    "gamma": 0.02,
                    "theta": -0.12,
                    "vega": 0.20,
                    "rho": -0.02,
                },
                "volume": 1500,
                "open_interest": 5500,
                "implied_volatility": 0.23,
            },
        ],
    }
    
    return mock_chain


def analyze_expected_structure():
    """分析我们期望的数据结构"""
    print_section("期权链数据结构验证 - 期望结构演示")
    
    print("\n说明：")
    print("  这个脚本展示了我们期望的期权链数据结构，即使没有权限也可以查看。")
    print("  当您获得权限后，可以用实际 API 返回的数据与这个结构对比。")
    
    # 创建模拟数据
    mock_chain = create_mock_option_chain("AAPL", 150.0)
    
    print_section("1. 顶层数据结构")
    
    print("\n顶层字段:")
    for key in sorted(mock_chain.keys()):
        value = mock_chain[key]
        if isinstance(value, list):
            print(f"  ✅ {key}: list ({len(value)} items)")
        elif isinstance(value, (int, float)):
            print(f"  ✅ {key}: {type(value).__name__} = {value}")
        else:
            print(f"  ✅ {key}: {type(value).__name__} = {value}")
    
    print_section("2. spot_price 检查")
    
    spot_price = mock_chain.get("spot_price") or mock_chain.get("underlying_price")
    if spot_price:
        print(f"✅ 找到 spot_price: {spot_price}")
        print(f"   字段名: {'spot_price' if 'spot_price' in mock_chain else 'underlying_price'}")
    else:
        print("❌ 未找到 spot_price")
    
    print_section("3. Calls 和 Puts 数组")
    
    calls = mock_chain.get("calls", [])
    puts = mock_chain.get("puts", [])
    
    print(f"\ncalls 数量: {len(calls)}")
    print(f"puts 数量: {len(puts)}")
    
    print_section("4. 期权对象字段（第一个 Call 期权）")
    
    if calls:
        first_call = calls[0]
        print(f"\n第一个 call 期权的字段:")
        print(f"  字段数量: {len(first_call)}")
        print(f"  字段列表:")
        for key in sorted(first_call.keys()):
            value = first_call[key]
            if isinstance(value, dict):
                print(f"    - {key}: dict (keys: {', '.join(value.keys())})")
            elif isinstance(value, (int, float)):
                print(f"    - {key}: {type(value).__name__} = {value}")
            else:
                print(f"    - {key}: {type(value).__name__}")
    
    print_section("5. Greeks 数据检查")
    
    if calls:
        first_call = calls[0]
        
        # 检查直接字段
        direct_greeks = {}
        greek_fields = ['delta', 'gamma', 'theta', 'vega', 'rho']
        for greek in greek_fields:
            if greek in first_call:
                direct_greeks[greek] = first_call[greek]
        
        # 检查嵌套对象
        nested_greeks = {}
        if "greeks" in first_call and isinstance(first_call["greeks"], dict):
            for greek in greek_fields:
                if greek in first_call["greeks"]:
                    nested_greeks[greek] = first_call["greeks"][greek]
        
        print(f"\n直接字段的 Greeks:")
        for greek in greek_fields:
            if greek in direct_greeks:
                print(f"  ✅ {greek}: {direct_greeks[greek]}")
            else:
                print(f"  ❌ {greek}: 不存在")
        
        if nested_greeks:
            print(f"\n嵌套 greeks 对象的 Greeks:")
            for greek in greek_fields:
                if greek in nested_greeks:
                    print(f"  ✅ greeks.{greek}: {nested_greeks[greek]}")
                else:
                    print(f"  ❌ greeks.{greek}: 不存在")
    
    print_section("6. 完整数据结构示例（JSON）")
    
    # 只显示第一个期权的详细信息
    sample_data = {
        "spot_price": mock_chain["spot_price"],
        "expiration_date": mock_chain["expiration_date"],
        "calls_count": len(mock_chain["calls"]),
        "puts_count": len(mock_chain["puts"]),
        "first_call_option": mock_chain["calls"][0] if mock_chain["calls"] else None,
        "first_put_option": mock_chain["puts"][0] if mock_chain["puts"] else None,
    }
    
    print(print_json(sample_data))
    
    print_section("7. 我们的代码如何处理这些数据")
    
    print("\n代码处理逻辑（backend/app/api/endpoints/market.py:63）:")
    print("  spot_price = chain_data.get('spot_price') or chain_data.get('underlying_price')")
    print("  calls = chain_data.get('calls', [])")
    print("  puts = chain_data.get('puts', [])")
    
    print("\n代码处理逻辑（backend/app/services/strategy_engine.py:68-105）:")
    print("  - 从期权对象中提取 Greeks（支持直接字段或嵌套对象）")
    print("  - 从期权对象中提取 bid/ask 价格")
    print("  - 使用 spot_price 选择执行价（通过 delta 匹配）")
    
    print_section("8. 关键验证点")
    
    print("\n需要验证的实际 API 返回数据:")
    print("  [ ] spot_price 是否在顶层？")
    print("  [ ] 字段名是 'spot_price' 还是 'underlying_price'？")
    print("  [ ] 每个期权对象是否包含 bid/ask 价格？")
    print("  [ ] 每个期权对象是否包含 Greeks？")
    print("  [ ] Greeks 是直接字段还是嵌套在 'greeks' 对象中？")
    print("  [ ] 是否包含所有必需的 Greeks（delta, gamma, theta, vega, rho）？")
    
    print_section("验证总结")
    
    print("\n期望的数据结构:")
    print("  ✅ 顶层包含 spot_price 或 underlying_price")
    print("  ✅ 包含 calls 和 puts 数组")
    print("  ✅ 每个期权对象包含 bid/ask 价格")
    print("  ✅ 每个期权对象包含 Greeks（直接字段或嵌套对象）")
    
    print("\n如果实际 API 返回的数据不符合这个结构:")
    print("  1. 如果缺少 spot_price → 需要调用 get_stock_briefs() 获取")
    print("  2. 如果缺少 Greeks → 需要自己实现 Black-Scholes 模型计算")
    print("  3. 如果字段名不同 → 需要调整数据提取逻辑")


if __name__ == "__main__":
    analyze_expected_structure()

