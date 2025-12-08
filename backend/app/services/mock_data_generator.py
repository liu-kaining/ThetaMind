"""
模拟数据生成器 - 用于在没有真实 API 权限时测试前端功能

生成符合 Tiger API 格式的模拟数据，包括：
- 期权链数据（calls, puts, spot_price, Greeks）
- 股票行情数据（price, change, change_percent, volume）
"""

import random
import math
from datetime import datetime, timedelta
from typing import Any


class MockDataGenerator:
    """生成模拟市场数据"""

    # 常见股票的基础价格（用于生成更真实的数据）
    BASE_PRICES = {
        "AAPL": 150.0,
        "TSLA": 250.0,
        "MSFT": 380.0,
        "GOOGL": 140.0,
        "AMZN": 150.0,
        "NVDA": 500.0,
        "META": 350.0,
        "SPY": 450.0,
        "QQQ": 380.0,
    }

    @staticmethod
    def _calculate_greeks(
        spot_price: float,
        strike: float,
        time_to_expiry: float,
        is_call: bool,
        volatility: float = 0.25,
        risk_free_rate: float = 0.05,
    ) -> dict[str, float]:
        """
        使用简化的 Black-Scholes 模型计算 Greeks
        
        这是一个简化版本，用于演示。实际应用中应该使用更精确的计算。
        """
        S = spot_price
        K = strike
        T = time_to_expiry / 365.0  # 转换为年
        r = risk_free_rate
        sigma = volatility

        # 简化的计算（实际应该使用 scipy.stats.norm 等）
        # 这里使用近似公式
        moneyness = S / K if K > 0 else 1.0
        time_factor = math.sqrt(T) if T > 0 else 0.01

        if is_call:
            # Call option Greeks (简化版)
            delta = max(0.0, min(1.0, 0.5 + (moneyness - 1.0) * 2))
            gamma = 0.02 * (1 - abs(moneyness - 1.0))
            theta = -0.15 - (0.1 * time_factor)
            vega = 0.25 * time_factor
            rho = 0.03 * T
        else:
            # Put option Greeks (简化版)
            delta = max(-1.0, min(0.0, -0.5 + (moneyness - 1.0) * 2))
            gamma = 0.02 * (1 - abs(moneyness - 1.0))
            theta = -0.15 - (0.1 * time_factor)
            vega = 0.25 * time_factor
            rho = -0.03 * T

        return {
            "delta": round(delta, 4),
            "gamma": round(gamma, 4),
            "theta": round(theta, 4),
            "vega": round(vega, 4),
            "rho": round(rho, 4),
        }

    @staticmethod
    def generate_option_chain(
        symbol: str,
        expiration_date: str,
        spot_price: float | None = None,
    ) -> dict[str, Any]:
        """
        生成模拟期权链数据
        
        Args:
            symbol: 股票代码
            expiration_date: 到期日期 (YYYY-MM-DD)
            spot_price: 标的价格（如果为 None，则使用基础价格）
        
        Returns:
            符合 OptionChainResponse 格式的字典
        """
        # 确定标的价格
        if spot_price is None:
            spot_price = MockDataGenerator.BASE_PRICES.get(
                symbol.upper(), 100.0
            ) * (0.9 + random.random() * 0.2)  # ±10% 波动

        # 计算到期时间
        exp_date = datetime.strptime(expiration_date, "%Y-%m-%d")
        today = datetime.now()
        days_to_expiry = (exp_date - today).days
        if days_to_expiry < 0:
            days_to_expiry = 30  # 如果已过期，默认30天

        # 生成执行价列表（围绕标的价格）
        strikes = []
        # ATM (at-the-money)
        atm_strike = round(spot_price / 5) * 5  # 四舍五入到最近的5
        
        # 生成执行价：从 ATM-30% 到 ATM+30%，每5美元一个
        strike_range = int(spot_price * 0.3 / 5)
        for i in range(-strike_range, strike_range + 1):
            strike = atm_strike + i * 5
            if strike > 0:
                strikes.append(strike)

        # 生成 Calls
        calls = []
        for strike in strikes:
            # 计算内在价值
            intrinsic = max(0, spot_price - strike)
            # 时间价值（简化）
            time_value = max(0.1, (spot_price * 0.05) * (days_to_expiry / 30))
            premium = intrinsic + time_value
            
            # 添加一些随机波动
            premium *= (0.95 + random.random() * 0.1)
            
            # 计算 Greeks
            greeks = MockDataGenerator._calculate_greeks(
                spot_price, strike, days_to_expiry, is_call=True
            )

            # Bid/Ask spread (约 2-5%)
            spread = premium * (0.02 + random.random() * 0.03)
            bid = max(0.01, premium - spread / 2)
            ask = premium + spread / 2

            calls.append({
                "strike": strike,
                "strike_price": strike,  # 备选字段名
                "bid": round(bid, 2),
                "ask": round(ask, 2),
                "bid_price": round(bid, 2),  # 备选字段名
                "ask_price": round(ask, 2),  # 备选字段名
                "last_price": round(premium, 2),
                "volume": random.randint(100, 5000),
                "open_interest": random.randint(1000, 20000),
                "delta": greeks["delta"],
                "gamma": greeks["gamma"],
                "theta": greeks["theta"],
                "vega": greeks["vega"],
                "rho": greeks["rho"],
                "greeks": greeks,  # 嵌套对象
                "implied_volatility": round(0.2 + random.random() * 0.15, 4),
                "iv": round(0.2 + random.random() * 0.15, 4),
                "contract_id": f"{symbol}{exp_date.strftime('%y%m%d')}C{int(strike*1000):08d}",
                "expiration": expiration_date,
                "days_to_expiration": days_to_expiry,
            })

        # 生成 Puts
        puts = []
        for strike in strikes:
            # 计算内在价值
            intrinsic = max(0, strike - spot_price)
            # 时间价值（简化）
            time_value = max(0.1, (spot_price * 0.05) * (days_to_expiry / 30))
            premium = intrinsic + time_value
            
            # 添加一些随机波动
            premium *= (0.95 + random.random() * 0.1)
            
            # 计算 Greeks
            greeks = MockDataGenerator._calculate_greeks(
                spot_price, strike, days_to_expiry, is_call=False
            )

            # Bid/Ask spread
            spread = premium * (0.02 + random.random() * 0.03)
            bid = max(0.01, premium - spread / 2)
            ask = premium + spread / 2

            puts.append({
                "strike": strike,
                "strike_price": strike,
                "bid": round(bid, 2),
                "ask": round(ask, 2),
                "bid_price": round(bid, 2),
                "ask_price": round(ask, 2),
                "last_price": round(premium, 2),
                "volume": random.randint(100, 5000),
                "open_interest": random.randint(1000, 20000),
                "delta": greeks["delta"],
                "gamma": greeks["gamma"],
                "theta": greeks["theta"],
                "vega": greeks["vega"],
                "rho": greeks["rho"],
                "greeks": greeks,
                "implied_volatility": round(0.2 + random.random() * 0.15, 4),
                "iv": round(0.2 + random.random() * 0.15, 4),
                "contract_id": f"{symbol}{exp_date.strftime('%y%m%d')}P{int(strike*1000):08d}",
                "expiration": expiration_date,
                "days_to_expiration": days_to_expiry,
            })

        return {
            "symbol": symbol.upper(),
            "expiration_date": expiration_date,
            "calls": calls,
            "puts": puts,
            "spot_price": round(spot_price, 2),
            "underlying_price": round(spot_price, 2),  # 备选字段名
            "_source": "mock",
        }

    @staticmethod
    def generate_stock_quote(symbol: str, base_price: float | None = None) -> dict[str, Any]:
        """
        生成模拟股票行情数据
        
        Args:
            symbol: 股票代码
            base_price: 基础价格（如果为 None，则使用基础价格）
        
        Returns:
            符合 StockQuoteResponse 格式的字典
        """
        # 确定基础价格
        if base_price is None:
            base_price = MockDataGenerator.BASE_PRICES.get(
                symbol.upper(), 100.0
            )

        # 生成当前价格（±2% 波动）
        price = base_price * (0.98 + random.random() * 0.04)
        
        # 计算涨跌（相对于前一天）
        change_percent = (random.random() - 0.5) * 4  # -2% 到 +2%
        change = price * change_percent / 100

        # 生成交易量
        volume = random.randint(1000000, 50000000)

        return {
            "symbol": symbol.upper(),
            "data": {
                "price": round(price, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "volume": volume,
                "high": round(price * 1.02, 2),
                "low": round(price * 0.98, 2),
                "open": round(price * (0.99 + random.random() * 0.02), 2),
                "prev_close": round(price - change, 2),
                "market_cap": round(price * volume * 0.1, 0),  # 简化计算
            },
            "is_pro": False,  # 模拟数据总是非 Pro
        }

    @staticmethod
    def generate_candlestick_data(
        symbol: str,
        days: int = 30,
        base_price: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        生成模拟K线数据（用于图表展示）
        
        Args:
            symbol: 股票代码
            days: 生成多少天的数据
            base_price: 基础价格
        
        Returns:
            CandlestickData 格式的列表（lightweight-charts 格式）
        """
        if base_price is None:
            base_price = MockDataGenerator.BASE_PRICES.get(
                symbol.upper(), 100.0
            )

        data = []
        current_price = base_price
        today = datetime.now()

        for i in range(days - 1, -1, -1):
            date = today - timedelta(days=i)
            
            # 生成 OHLC（简化随机游走模型）
            daily_change = (random.random() - 0.5) * 0.03  # ±1.5% 日波动
            open_price = current_price
            close_price = open_price * (1 + daily_change)
            high_price = max(open_price, close_price) * (1 + random.random() * 0.01)
            low_price = min(open_price, close_price) * (1 - random.random() * 0.01)

            # 转换为 lightweight-charts 格式
            # time 格式：YYYY-MM-DD 或 timestamp
            data.append({
                "time": date.strftime("%Y-%m-%d"),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
            })

            current_price = close_price

        return data


# 单例实例
mock_data_generator = MockDataGenerator()

