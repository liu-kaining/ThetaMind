"""Unit tests for StrategyEngine.

Tests mathematical correctness, edge cases, and validation logic.
"""

import pytest
from datetime import datetime, timedelta

from app.schemas.strategy_recommendation import (
    OptionLeg,
    OptionType,
    Outlook,
    RiskProfile,
)
from app.services.strategy_engine import StrategyEngine


class TestFindOption:
    """Test _find_option method."""

    def test_find_closest_option(self):
        """Test finding option closest to target delta."""
        engine = StrategyEngine()

        # Mock option chain with deltas [0.1, 0.25, 0.4]
        chain = {
            "calls": [
                {"strike": 100, "delta": 0.1, "bid": 1.0, "ask": 1.1},
                {"strike": 105, "delta": 0.25, "bid": 2.0, "ask": 2.1},
                {"strike": 110, "delta": 0.4, "bid": 3.0, "ask": 3.1},
            ],
            "puts": [],
        }

        # Request target 0.3
        result = engine._find_option(chain, OptionType.CALL, 0.3, 100.0)

        # Assert it returns the option with delta 0.25 (closest to 0.3)
        assert result is not None
        assert result["delta"] == 0.25
        assert result["strike"] == 105

    def test_find_option_empty_chain(self):
        """Test _find_option with empty chain."""
        engine = StrategyEngine()
        chain = {"calls": [], "puts": []}

        result = engine._find_option(chain, OptionType.CALL, 0.3, 100.0)

        assert result is None

    def test_find_option_no_delta(self):
        """Test _find_option when options have no delta."""
        engine = StrategyEngine()
        chain = {
            "calls": [
                {"strike": 100, "bid": 1.0, "ask": 1.1},  # No delta field
            ],
            "puts": [],
        }

        result = engine._find_option(chain, OptionType.CALL, 0.3, 100.0)

        assert result is None


class TestLiquidityValidation:
    """Test liquidity validation logic."""

    def test_validate_liquidity_good_spread(self):
        """Test liquidity validation with good spreads."""
        engine = StrategyEngine()

        legs = [
            OptionLeg(
                symbol="AAPL",
                strike=100.0,
                ratio=1,
                type=OptionType.CALL,
                greeks={},
                bid=1.0,
                ask=1.05,  # 5% spread
                mid_price=1.025,
                expiration_date="2024-02-16",
                days_to_expiration=30,
            ),
        ]

        assert engine._validate_liquidity(legs) is True

    def test_liquidity_filter_wide_spread(self):
        """Test liquidity filter rejects wide spreads."""
        engine = StrategyEngine()

        # Mock a chain where ask - bid is huge ($5.00 vs $6.00)
        # Spread = $1.00, Mid = $5.50, Spread % = 18.18% > 10%
        legs = [
            OptionLeg(
                symbol="AAPL",
                strike=100.0,
                ratio=1,
                type=OptionType.CALL,
                greeks={},
                bid=5.00,
                ask=6.00,  # $1.00 spread, 18.18% of mid
                mid_price=5.50,
                expiration_date="2024-02-16",
                days_to_expiration=30,
            ),
        ]

        assert engine._validate_liquidity(legs) is False

    def test_validate_liquidity_zero_mid_price(self):
        """Test liquidity validation with zero mid price."""
        engine = StrategyEngine()

        legs = [
            OptionLeg(
                symbol="AAPL",
                strike=100.0,
                ratio=1,
                type=OptionType.CALL,
                greeks={},
                bid=0.0,
                ask=0.0,
                mid_price=0.0,  # Invalid
                expiration_date="2024-02-16",
                days_to_expiration=30,
            ),
        ]

        assert engine._validate_liquidity(legs) is False


class TestIronCondorGeneration:
    """Test Iron Condor strategy generation."""

    def test_iron_condor_generation(self):
        """Test Iron Condor generation with high liquidity."""
        engine = StrategyEngine()

        # Calculate expiration date (45 days from now)
        expiration_date = (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")

        # Mock a chain with high liquidity and proper Greeks
        spot_price = 100.0
        chain = {
            "calls": [
                {
                    "strike": 105.0,
                    "delta": 0.20,  # Target for short call
                    "bid": 2.0,
                    "ask": 2.05,
                    "greeks": {"delta": 0.20, "gamma": 0.01, "theta": -0.05, "vega": 0.1},
                },
                {
                    "strike": 110.0,  # Long call (wing)
                    "delta": 0.10,
                    "bid": 0.5,
                    "ask": 0.55,
                    "greeks": {"delta": 0.10, "gamma": 0.005, "theta": -0.02, "vega": 0.05},
                },
            ],
            "puts": [
                {
                    "strike": 95.0,
                    "delta": -0.20,  # Target for short put
                    "bid": 2.0,
                    "ask": 2.05,
                    "greeks": {"delta": -0.20, "gamma": 0.01, "theta": -0.05, "vega": 0.1},
                },
                {
                    "strike": 90.0,  # Long put (wing)
                    "delta": -0.10,
                    "bid": 0.5,
                    "ask": 0.55,
                    "greeks": {"delta": -0.10, "gamma": 0.005, "theta": -0.02, "vega": 0.05},
                },
            ],
            "spot_price": spot_price,
        }

        # Run generate_strategies with Outlook.NEUTRAL
        strategies = engine.generate_strategies(
            chain=chain,
            symbol="AAPL",
            spot_price=spot_price,
            outlook=Outlook.NEUTRAL,
            risk_profile=RiskProfile.CONSERVATIVE,
            capital=10000.0,
            expiration_date=expiration_date,
        )

        # Assert it returns at least 1 strategy
        assert len(strategies) >= 1

        strategy = strategies[0]

        # Assert strategy is Iron Condor
        assert "Iron Condor" in strategy.name
        assert len(strategy.legs) == 4

        # Extract metrics
        max_profit = strategy.metrics["max_profit"]
        max_loss = strategy.metrics["max_loss"]
        
        # Calculate actual wing width from strikes
        # Iron Condor: Short Call (leg 0), Long Call (leg 1), Short Put (leg 2), Long Put (leg 3)
        call_wing = strategy.legs[1].strike - strategy.legs[0].strike  # Long call - Short call
        put_wing = strategy.legs[2].strike - strategy.legs[3].strike  # Short put - Long put
        actual_wing_width = max(call_wing, put_wing)  # Should be same, but take max for safety

        # CRUCIAL: Assert max_loss + max_profit == strike_width
        # For Iron Condor: max_profit = net_credit, max_loss = wing_width - net_credit
        # Therefore: max_profit + max_loss = wing_width
        assert abs((max_profit + max_loss) - actual_wing_width) < 0.01, (
            f"Iron Condor math check failed: max_profit ({max_profit}) + max_loss ({max_loss}) "
            f"= {max_profit + max_loss}, expected wing_width ≈ {actual_wing_width}"
        )

        # Additional checks
        assert max_profit > 0, "Max profit should be positive (net credit)"
        assert max_loss > 0, "Max loss should be positive"
        assert strategy.metrics["risk_reward_ratio"] > 0
        assert 0 <= strategy.metrics["pop"] <= 1, "POP should be between 0 and 1"
        assert abs(strategy.metrics["net_greeks"]["delta"]) < 0.10, "Should be delta neutral"

    def test_iron_condor_liquidity_filter(self):
        """Test that Iron Condor is filtered out if liquidity is bad."""
        engine = StrategyEngine()

        expiration_date = (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")
        spot_price = 100.0

        # Mock a chain with WIDE spreads (bad liquidity)
        chain = {
            "calls": [
                {
                    "strike": 105.0,
                    "delta": 0.20,
                    "bid": 1.0,
                    "ask": 2.0,  # 50% spread - should be rejected
                    "greeks": {"delta": 0.20},
                },
                {
                    "strike": 110.0,
                    "delta": 0.10,
                    "bid": 0.5,
                    "ask": 1.0,  # 50% spread
                    "greeks": {"delta": 0.10},
                },
            ],
            "puts": [
                {
                    "strike": 95.0,
                    "delta": -0.20,
                    "bid": 1.0,
                    "ask": 2.0,  # 50% spread
                    "greeks": {"delta": -0.20},
                },
                {
                    "strike": 90.0,
                    "delta": -0.10,
                    "bid": 0.5,
                    "ask": 1.0,  # 50% spread
                    "greeks": {"delta": -0.10},
                },
            ],
            "spot_price": spot_price,
        }

        strategies = engine.generate_strategies(
            chain=chain,
            symbol="AAPL",
            spot_price=spot_price,
            outlook=Outlook.NEUTRAL,
            risk_profile=RiskProfile.CONSERVATIVE,
            capital=10000.0,
            expiration_date=expiration_date,
        )

        # Assert generate_strategies returns Zero results (filtered out)
        assert len(strategies) == 0, "Strategies with bad liquidity should be filtered out"


class TestBullCallSpread:
    """Test Bull Call Spread generation."""

    def test_bull_call_spread_generation(self):
        """Test Bull Call Spread generation."""
        engine = StrategyEngine()

        expiration_date = (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")
        spot_price = 100.0

        chain = {
            "calls": [
                {
                    "strike": 95.0,  # ITM, delta ~0.65 (buy leg)
                    "delta": 0.65,
                    "bid": 8.0,
                    "ask": 8.1,
                    "greeks": {"delta": 0.65, "gamma": 0.02, "theta": -0.1, "vega": 0.2},
                },
                {
                    "strike": 105.0,  # OTM, delta ~0.30 (sell leg)
                    "delta": 0.30,
                    "bid": 2.0,
                    "ask": 2.1,
                    "greeks": {"delta": 0.30, "gamma": 0.01, "theta": -0.05, "vega": 0.1},
                },
            ],
            "puts": [],
            "spot_price": spot_price,
        }
        
        # Debug: Check if options are found
        buy_call = engine._find_option(chain, OptionType.CALL, 0.65, spot_price)
        sell_call = engine._find_option(chain, OptionType.CALL, 0.30, spot_price)
        
        # Ensure options are found
        assert buy_call is not None, "Buy call option not found"
        assert sell_call is not None, "Sell call option not found"
        
        # Verify strikes are correct (buy < sell for bull call spread)
        buy_strike = float(buy_call.get("strike", buy_call.get("strike_price", 0.0)))
        sell_strike = float(sell_call.get("strike", sell_call.get("strike_price", 0.0)))
        assert buy_strike < sell_strike, f"Buy strike ({buy_strike}) must be < sell strike ({sell_strike})"
        
        # Calculate expected net debit
        net_debit = buy_call["ask"] - sell_call["bid"]  # 8.1 - 2.0 = 6.1
        spread_width = sell_strike - buy_strike  # 105 - 95 = 10
        max_debit_allowed = spread_width * 0.50  # 10 * 0.5 = 5.0
        
        # Net debit (6.1) > max allowed (5.0), so it should be filtered
        # Let's adjust the prices to pass the validation
        chain["calls"][0]["ask"] = 7.0  # Lower buy ask
        chain["calls"][1]["bid"] = 2.5  # Higher sell bid
        # New net_debit = 7.0 - 2.5 = 4.5 < 5.0 (passes validation)

        strategies = engine.generate_strategies(
            chain=chain,
            symbol="AAPL",
            spot_price=spot_price,
            outlook=Outlook.BULLISH,
            risk_profile=RiskProfile.CONSERVATIVE,
            capital=10000.0,
            expiration_date=expiration_date,
        )

        assert len(strategies) >= 1

        strategy = strategies[0]
        assert "Bull Call Spread" in strategy.name
        assert len(strategy.legs) == 2

        # Verify math: max_profit + max_loss = spread_width
        max_profit = strategy.metrics["max_profit"]
        max_loss = strategy.metrics["max_loss"]
        spread_width = 105.0 - 95.0  # 10.0

        assert abs((max_profit + max_loss) - spread_width) < 0.01, (
            f"Bull Call Spread math check failed: max_profit ({max_profit}) + max_loss ({max_loss}) "
            f"= {max_profit + max_loss}, expected {spread_width}"
        )


class TestNetGreeks:
    """Test net Greeks calculation."""

    def test_calculate_net_greeks(self):
        """Test net Greeks calculation with multiple legs."""
        engine = StrategyEngine()

        legs = [
            OptionLeg(
                symbol="AAPL",
                strike=100.0,
                ratio=+1,  # Buy
                type=OptionType.CALL,
                greeks={"delta": 0.5, "gamma": 0.1, "theta": -0.05, "vega": 0.2, "rho": 0.01},
                bid=5.0,
                ask=5.1,
                mid_price=5.05,
                expiration_date="2024-02-16",
                days_to_expiration=30,
            ),
            OptionLeg(
                symbol="AAPL",
                strike=105.0,
                ratio=-1,  # Sell
                type=OptionType.CALL,
                greeks={"delta": 0.3, "gamma": 0.05, "theta": -0.02, "vega": 0.1, "rho": 0.005},
                bid=2.0,
                ask=2.1,
                mid_price=2.05,
                expiration_date="2024-02-16",
                days_to_expiration=30,
            ),
        ]

        net_greeks = engine._calculate_net_greeks(legs)

        # Net delta = (+1 * 0.5) + (-1 * 0.3) = 0.2
        assert abs(net_greeks["delta"] - 0.2) < 0.001
        # Net gamma = (+1 * 0.1) + (-1 * 0.05) = 0.05
        assert abs(net_greeks["gamma"] - 0.05) < 0.001
        # Net theta = (+1 * -0.05) + (-1 * -0.02) = -0.03
        assert abs(net_greeks["theta"] - (-0.03)) < 0.001


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_chain(self):
        """Test with completely empty chain."""
        engine = StrategyEngine()

        chain = {"calls": [], "puts": [], "spot_price": 100.0}

        strategies = engine.generate_strategies(
            chain=chain,
            symbol="AAPL",
            spot_price=100.0,
            outlook=Outlook.NEUTRAL,
            risk_profile=RiskProfile.CONSERVATIVE,
            capital=10000.0,
            expiration_date="2024-02-16",
        )

        assert len(strategies) == 0

    def test_missing_expiration_date(self):
        """Test with missing expiration date."""
        engine = StrategyEngine()

        chain = {
            "calls": [],
            "puts": [],
            "spot_price": 100.0,
        }

        strategies = engine.generate_strategies(
            chain=chain,
            symbol="AAPL",
            spot_price=100.0,
            outlook=Outlook.NEUTRAL,
            risk_profile=RiskProfile.CONSERVATIVE,
            capital=10000.0,
            expiration_date=None,
        )

        # Should return empty list if no expiration_date in chain
        assert isinstance(strategies, list)

    def test_liquidity_score_empty_legs(self):
        """Test liquidity score calculation with empty legs."""
        engine = StrategyEngine()

        score = engine._calculate_liquidity_score([])
        assert score == 0.0

    def test_liquidity_score_calculation(self):
        """Test liquidity score calculation."""
        engine = StrategyEngine()

        legs = [
            OptionLeg(
                symbol="AAPL",
                strike=100.0,
                ratio=1,
                type=OptionType.CALL,
                greeks={},
                bid=1.0,
                ask=1.05,  # 5% spread
                mid_price=1.025,
                expiration_date="2024-02-16",
                days_to_expiration=30,
            ),
        ]

        score = engine._calculate_liquidity_score(legs)
        # 5% spread should give score = 100 - (5 * 10) = 50
        # Actual calculation: spread = 0.05, spread_pct = (0.05 / 1.025) * 100 = 4.878%
        # score = 100 - (4.878 * 10) = 51.22
        assert abs(score - 51.22) < 0.1, f"Expected score ~51.22, got {score}"

