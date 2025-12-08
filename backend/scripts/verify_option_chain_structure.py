"""
验证 Tiger API get_option_chain() 返回的数据结构

使用方法:
    docker-compose exec backend python scripts/verify_option_chain_structure.py
"""
import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
# 在 Docker 容器中，工作目录是 /app
script_dir = Path(__file__).parent
backend_dir = script_dir.parent
sys.path.insert(0, str(backend_dir))

from app.services.tiger_service import tiger_service


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


async def verify_structure(symbol: str = "AAPL"):
    """验证期权链数据结构"""
    print_section("Tiger API 期权链数据结构验证")
    
    # 检查服务是否初始化
    if not tiger_service._client:
        print("❌ TigerService 未初始化")
        print("   请检查环境变量和权限配置")
        return
    
    # 计算未来日期（30天后）
    future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    print(f"\n测试参数:")
    print(f"  Symbol: {symbol}")
    print(f"  Expiration Date: {future_date}")
    
    try:
        print_section("1. 调用 get_option_chain() API")
        
        # 调用 API
        chain_data = await tiger_service.get_option_chain(symbol, future_date)
        
        print("✅ API 调用成功")
        
        print_section("2. 顶层数据结构")
        
        # 打印顶层字段
        if isinstance(chain_data, dict):
            top_level_keys = list(chain_data.keys())
            print(f"\n顶层字段 ({len(top_level_keys)} 个):")
            for key in sorted(top_level_keys):
                value = chain_data[key]
                if isinstance(value, (list, dict)):
                    print(f"  - {key}: {type(value).__name__} ({len(value) if hasattr(value, '__len__') else 'N/A'})")
                else:
                    print(f"  - {key}: {type(value).__name__} = {value}")
        else:
            print(f"数据类型: {type(chain_data)}")
            print(f"数据: {chain_data}")
        
        print_section("3. spot_price 检查")
        
        # 检查 spot_price
        spot_price = chain_data.get("spot_price") or chain_data.get("underlying_price") or chain_data.get("underlyingPrice")
        if spot_price:
            print(f"✅ 找到 spot_price: {spot_price}")
            print(f"   字段名: {'spot_price' if 'spot_price' in chain_data else 'underlying_price' if 'underlying_price' in chain_data else 'underlyingPrice'}")
        else:
            print("❌ 未找到 spot_price")
            print("   检查的字段: spot_price, underlying_price, underlyingPrice")
            print("   可能需要单独调用 get_stock_briefs() 获取股票价格")
        
        print_section("4. Calls 和 Puts 数组检查")
        
        # 检查 calls 和 puts
        calls = chain_data.get("calls", [])
        puts = chain_data.get("puts", [])
        
        print(f"\ncalls 数量: {len(calls)}")
        print(f"puts 数量: {len(puts)}")
        
        if calls:
            print(f"\n✅ 找到 calls 数组")
        else:
            print(f"\n⚠️  calls 数组为空或不存在")
        
        if puts:
            print(f"✅ 找到 puts 数组")
        else:
            print(f"⚠️  puts 数组为空或不存在")
        
        print_section("5. 期权对象字段检查")
        
        # 检查第一个期权的字段
        if calls:
            first_call = calls[0]
            print(f"\n第一个 call 期权的字段:")
            
            if isinstance(first_call, dict):
                option_keys = list(first_call.keys())
                print(f"  字段数量: {len(option_keys)}")
                print(f"  字段列表: {', '.join(sorted(option_keys))}")
                
                # 检查关键字段
                print(f"\n  关键字段检查:")
                key_fields = ['strike', 'strike_price', 'bid', 'ask', 'delta', 'gamma', 'theta', 'vega', 'rho', 'greeks']
                for field in key_fields:
                    if field in first_call:
                        value = first_call[field]
                        if isinstance(value, dict):
                            print(f"    ✅ {field}: dict with keys {list(value.keys())}")
                        else:
                            print(f"    ✅ {field}: {value}")
                    else:
                        print(f"    ❌ {field}: 不存在")
                
                # 打印示例数据（限制长度）
                print(f"\n  示例数据（前 3 个字段）:")
                for i, (key, value) in enumerate(list(first_call.items())[:3]):
                    if isinstance(value, (dict, list)):
                        print(f"    {key}: {type(value).__name__} ({len(value) if hasattr(value, '__len__') else 'N/A'})")
                    else:
                        print(f"    {key}: {value}")
            else:
                print(f"  数据类型: {type(first_call)}")
                print(f"  数据: {first_call}")
        
        print_section("6. Greeks 数据检查")
        
        # 检查 Greeks
        has_greeks = False
        greek_fields = ['delta', 'gamma', 'theta', 'vega', 'rho']
        
        if calls:
            first_call = calls[0]
            if isinstance(first_call, dict):
                # 检查直接字段
                direct_greeks = {}
                for greek in greek_fields:
                    if greek in first_call:
                        direct_greeks[greek] = first_call[greek]
                
                # 检查嵌套 greeks 对象
                nested_greeks = {}
                if "greeks" in first_call and isinstance(first_call["greeks"], dict):
                    for greek in greek_fields:
                        if greek in first_call["greeks"]:
                            nested_greeks[greek] = first_call["greeks"][greek]
                
                if direct_greeks:
                    has_greeks = True
                    print(f"✅ 找到直接字段的 Greeks:")
                    for greek, value in direct_greeks.items():
                        print(f"    {greek}: {value}")
                
                if nested_greeks:
                    has_greeks = True
                    print(f"✅ 找到嵌套 greeks 对象的 Greeks:")
                    for greek, value in nested_greeks.items():
                        print(f"    greeks.{greek}: {value}")
                
                if not has_greeks:
                    print("❌ 未找到 Greeks 数据")
                    print("   可能需要自己计算（使用 Black-Scholes 模型）")
        
        print_section("7. 完整数据结构示例（JSON）")
        
        # 打印完整结构（限制深度）
        sample_data = {
            "top_level_keys": list(chain_data.keys()) if isinstance(chain_data, dict) else [],
            "spot_price": spot_price,
            "calls_count": len(calls),
            "puts_count": len(puts),
        }
        
        if calls and len(calls) > 0:
            first_call_sample = {}
            first_call = calls[0]
            if isinstance(first_call, dict):
                # 只取前 10 个字段
                for key, value in list(first_call.items())[:10]:
                    if isinstance(value, (dict, list)):
                        first_call_sample[key] = f"{type(value).__name__}({len(value) if hasattr(value, '__len__') else 'N/A'})"
                    else:
                        first_call_sample[key] = value
            sample_data["first_call_sample"] = first_call_sample
        
        print(print_json(sample_data))
        
        print_section("验证总结")
        
        # 总结
        print("\n验证结果:")
        print(f"  ✅ API 调用: 成功")
        print(f"  {'✅' if spot_price else '❌'} spot_price: {'找到' if spot_price else '未找到'}")
        print(f"  {'✅' if calls else '❌'} calls 数组: {'存在' if calls else '不存在'}")
        print(f"  {'✅' if puts else '❌'} puts 数组: {'存在' if puts else '不存在'}")
        print(f"  {'✅' if has_greeks else '❌'} Greeks 数据: {'找到' if has_greeks else '未找到'}")
        
        print("\n建议:")
        if not spot_price:
            print("  - 如果 spot_price 不存在，需要调用 get_stock_briefs() 获取股票价格")
            print("  - 或者使用替代数据源（如 Yahoo Finance）")
        if not has_greeks:
            print("  - 如果 Greeks 不存在，需要使用 Tiger SDK 的计算工具或自己实现 Black-Scholes 模型")
        
    except Exception as e:
        print_section("错误信息")
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        
        print("\n可能的原因:")
        print("  1. 权限不足（需要 usOptionQuote 权限）")
        print("  2. 网络连接问题")
        print("  3. API 参数错误")
        print("  4. 服务未初始化")


if __name__ == "__main__":
    # 从命令行参数获取 symbol，默认使用 AAPL
    symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    
    asyncio.run(verify_structure(symbol))

