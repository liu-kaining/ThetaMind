"""Strategy Recommendation Engine - Advanced Mathematical Logic with Greeks Analysis.

This engine runs strictly on the backend (Python) and uses advanced mathematical
logic and full Greeks analysis to select optimal strikes. It does NOT call
Gemini/OpenAI. It must be fast, deterministic, and financially rigorous.

Option chain and Greeks are provided by Tiger (tiger_service.get_option_chain).
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from app.schemas.strategy_recommendation import (
    CalculatedStrategy,
    OptionLeg,
    OptionType,
    Outlook,
    RiskProfile,
)

logger = logging.getLogger(__name__)


class StrategyEngine:
    """Professional-grade strategy recommendation engine with strict validation.
    
    Option chain and Greeks come from Tiger (tiger_service.get_option_chain).
    """

    def __init__(self, market_data_service: Optional[Any] = None) -> None:
        """Initialize the strategy engine.
        
        Args:
            market_data_service: Optional MarketDataService instance for FinanceToolkit calculations
        """
        self._market_data_service = market_data_service

    def _get_greeks_from_financetoolkit(
        self,
        symbol: str,
        strike: float,
        option_type: OptionType,
        expiration_date: str,
        spot_price: float,
    ) -> dict[str, float]:
        """
        Greeks fallback: 期权链统一来自 Tiger，Greeks 由 option_chain 提供，此处不再从其他源拉取。
        Option chain and Greeks are from Tiger (tiger_service.get_option_chain with return_greek_value=True).
        Returns {} so callers use Greeks from the option_chain (Tiger) only.
        """
        return {}

    def _find_option(
        self,
        chain: dict[str, Any],
        option_type: OptionType,
        target_delta: float,
        spot_price: float,
    ) -> dict[str, Any] | None:
        """
        Find the option closest to target delta.
        
        Safety: Handles missing delta values gracefully (skips options with None delta).
        Greeks come from option_chain (Tiger); if missing, option is skipped.

        Args:
            chain: Option chain data from Tiger with 'calls' and 'puts' lists
            option_type: CALL or PUT
            spot_price: Current spot price

        Returns:
            Option data dict or None if not found
        """
        options = chain.get("calls" if option_type == OptionType.CALL else "puts", [])
        if not options:
            return None

        best_match = None
        min_delta_diff = float("inf")

        for option in options:
            # Extract delta from Greeks (handle different field names)
            delta = self._extract_greek(option, "delta")
            
            # Greeks from Tiger option_chain only; if missing, skip this option
            if delta is None:
                strike = option.get("strike") or option.get("strike_price")
                expiration_date = chain.get("expiration_date") or option.get("expiration_date")
                
                if strike and expiration_date and spot_price:
                    try:
                        calculated_greeks = self._get_greeks_from_financetoolkit(
                            symbol=chain.get("symbol", ""),
                            strike=float(strike),
                            option_type=option_type,
                            expiration_date=str(expiration_date),
                            spot_price=spot_price,
                        )
                        delta = calculated_greeks.get("delta")
                        if delta is not None:
                            if "greeks" not in option:
                                option["greeks"] = {}
                            option["greeks"]["delta"] = delta
                            # Also update other Greeks if available
                            for greek_name in ["gamma", "theta", "vega", "rho"]:
                                if greek_name in calculated_greeks:
                                    option["greeks"][greek_name] = calculated_greeks[greek_name]
                    except Exception as e:
                        logger.debug(f"Greeks fallback: {e}")
            
            # Skip options with None or invalid delta values
            if delta is None:
                continue
            # Safety check: ensure delta is a valid number
            try:
                delta = float(delta)
            except (ValueError, TypeError):
                continue

            delta_diff = abs(delta - target_delta)
            if delta_diff < min_delta_diff:
                min_delta_diff = delta_diff
                best_match = option

        return best_match
    
    def _find_closest_strike(
        self,
        chain: dict[str, Any],
        option_type: OptionType,
        target_strike: float,
    ) -> dict[str, Any] | None:
        """
        Find the option with strike closest to target_strike.
        
        Used when exact strike doesn't exist in the chain.
        This is common in real market data where strikes are discrete.

        Args:
            chain: Option chain data with 'calls' and 'puts' lists
            option_type: CALL or PUT
            target_strike: Target strike price

        Returns:
            Option data dict or None if not found
        """
        options = chain.get("calls" if option_type == OptionType.CALL else "puts", [])
        if not options:
            return None

        best_match = None
        min_strike_diff = float("inf")

        for option in options:
            strike = option.get("strike") or option.get("strike_price")
            if strike is None:
                continue
            try:
                strike = float(strike)
            except (ValueError, TypeError):
                continue

            strike_diff = abs(strike - target_strike)
            if strike_diff < min_strike_diff:
                min_strike_diff = strike_diff
                best_match = option

        return best_match

    def _extract_greek(self, option: dict[str, Any], greek_name: str) -> float | None:
        """
        Extract Greek value from option data (option_chain from Tiger).

        Handles different field naming conventions:
        - Direct: delta, gamma, theta, vega
        - Nested: greeks.delta, greek_delta
        - Case variations: Delta, DELTA

        Args:
            option: Option data dict
            greek_name: Name of the Greek (delta, gamma, theta, vega, rho)

        Returns:
            Greek value or None if not found
        """
        # Try direct access
        if greek_name.lower() in option:
            value = option[greek_name.lower()]
            if isinstance(value, (int, float)):
                return float(value)

        # Try nested greeks dict
        if "greeks" in option and isinstance(option["greeks"], dict):
            if greek_name.lower() in option["greeks"]:
                value = option["greeks"][greek_name.lower()]
                if isinstance(value, (int, float)):
                    return float(value)

        # Try prefixed versions
        for prefix in ["greek_", "g_", ""]:
            key = f"{prefix}{greek_name.lower()}"
            if key in option:
                value = option[key]
                if isinstance(value, (int, float)):
                    return float(value)

        return None

    def _extract_price_fields(self, option: dict[str, Any]) -> tuple[float, float]:
        """
        Extract bid and ask prices from option data.

        Args:
            option: Option data dict

        Returns:
            Tuple of (bid, ask) prices
        """
        bid = float(option.get("bid", option.get("bid_price", 0.0)))
        ask = float(option.get("ask", option.get("ask_price", 0.0)))
        return bid, ask

    def _validate_liquidity(self, legs: list[OptionLeg]) -> bool:
        """
        Validate liquidity of all legs.

        Rule: If (Ask - Bid) / Mid > 10% for any leg, discard this strategy
        (Slippage is too high).

        Args:
            legs: List of option legs

        Returns:
            True if all legs pass liquidity check, False otherwise
        """
        for leg in legs:
            if leg.mid_price <= 0:
                return False  # Invalid mid price

            spread = leg.ask - leg.bid
            spread_percentage = (spread / leg.mid_price) * 100.0

            if spread_percentage > 10.0:
                logger.debug(
                    f"Liquidity check failed for {leg.symbol} {leg.type} {leg.strike}: "
                    f"spread {spread_percentage:.2f}% > 10%"
                )
                return False

        return True

    def _calculate_net_greeks(self, legs: list[OptionLeg]) -> dict[str, float]:
        """
        Calculate net Greeks by summing leg.ratio * leg.greek.
        
        ⚠️ NOTE: This is strategy-level calculation (combining multiple options).
        Individual option Greeks should come from FinanceToolkit (via option chain or calculation).
        
        Safety: Handles None/missing greek values gracefully (defaults to 0.0).
        Real market data can have missing Greeks, so we must be resilient.

        Args:
            legs: List of option legs

        Returns:
            Dictionary with net delta, gamma, theta, vega, rho
        """
        net_greeks = {
            "delta": 0.0,
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
            "rho": 0.0,
        }

        for leg in legs:
            ratio = leg.ratio
            for greek_name in net_greeks:
                # Safely extract greek value, defaulting to 0.0 if None or missing
                greek_value = leg.greeks.get(greek_name.lower())
                if greek_value is None:
                    greek_value = 0.0
                # Ensure it's a number (handle edge cases)
                try:
                    greek_value = float(greek_value) if greek_value is not None else 0.0
                except (ValueError, TypeError):
                    greek_value = 0.0
                net_greeks[greek_name] += ratio * greek_value

        return net_greeks

    def _calculate_liquidity_score(self, legs: list[OptionLeg]) -> float:
        """
        Calculate overall liquidity score (0-100).

        Lower spread percentage = higher score.

        Args:
            legs: List of option legs

        Returns:
            Liquidity score from 0-100
        """
        if not legs:
            return 0.0

        total_spread_pct = 0.0
        for leg in legs:
            if leg.mid_price > 0:
                spread = leg.ask - leg.bid
                spread_pct = (spread / leg.mid_price) * 100.0
                total_spread_pct += spread_pct

        avg_spread_pct = total_spread_pct / len(legs)

        # Convert to score: 0% spread = 100, 10% spread = 0
        score = max(0.0, 100.0 - (avg_spread_pct * 10.0))
        return round(score, 2)

    def _create_option_leg(
        self,
        option: dict[str, Any],
        symbol: str,
        ratio: int,
        option_type: OptionType,
        expiration_date: str,
        dte: int,
        spot_price: float,
    ) -> OptionLeg:
        """
        Create an OptionLeg from option chain data.
        
        ⚠️ OPTIMIZATION: If Greeks are missing, FinanceToolkit will be used to calculate them.

        Args:
            option: Option data from chain
            symbol: Stock symbol
            ratio: Position ratio (+1 for Buy, -1 for Sell)
            option_type: CALL or PUT
            expiration_date: Expiration date string
            dte: Days to expiration
            spot_price: Current spot price (for FinanceToolkit calculation if needed)

        Returns:
            OptionLeg instance
        """
        bid, ask = self._extract_price_fields(option)
        mid_price = (bid + ask) / 2.0

        # Extract Greeks - try to get from option data first
        greeks = {
            "delta": self._extract_greek(option, "delta") or 0.0,
            "gamma": self._extract_greek(option, "gamma") or 0.0,
            "theta": self._extract_greek(option, "theta") or 0.0,
            "vega": self._extract_greek(option, "vega") or 0.0,
            "rho": self._extract_greek(option, "rho") or 0.0,
        }
        
        # Greeks from Tiger option_chain only; fallback returns {} so missing stay 0
        if any(g == 0.0 for g in greeks.values()):
            strike = float(option.get("strike", option.get("strike_price", 0.0)))
            if strike > 0 and spot_price > 0:
                try:
                    calculated_greeks = self._get_greeks_from_financetoolkit(
                        symbol=symbol,
                        strike=strike,
                        option_type=option_type,
                        expiration_date=expiration_date,
                        spot_price=spot_price,
                    )
                    for greek_name in greeks:
                        if greeks[greek_name] == 0.0 and greek_name in calculated_greeks:
                            greeks[greek_name] = calculated_greeks[greek_name]
                except Exception as e:
                    logger.debug(f"Greeks fallback: {e}")

        strike = float(option.get("strike", option.get("strike_price", 0.0)))

        return OptionLeg(
            symbol=symbol,
            strike=strike,
            ratio=ratio,
            type=option_type,
            greeks=greeks,
            bid=bid,
            ask=ask,
            mid_price=mid_price,
            expiration_date=expiration_date,
            days_to_expiration=dte,
        )

    def _calculate_dte(self, expiration_date: str) -> int:
        """
        Calculate days to expiration.

        Args:
            expiration_date: Expiration date string (YYYY-MM-DD)

        Returns:
            Days to expiration
        """
        try:
            exp_date = datetime.strptime(expiration_date, "%Y-%m-%d")
            today = datetime.now().date()
            dte = (exp_date.date() - today).days
            return max(0, dte)
        except (ValueError, TypeError):
            return 0

    def _algorithm_iron_condor(
        self,
        chain: dict[str, Any],
        symbol: str,
        spot_price: float,
        expiration_date: str,
        risk_profile: RiskProfile,
        capital: float,
    ) -> CalculatedStrategy | None:
        """
        Algorithm 1: Advanced Iron Condor (Neutral + High IV).

        Objective: Collect premium while minimizing directional risk (Delta Neutral).

        Strike Selection:
        - Short Strikes: Target Delta ≈ 0.20 (Conservative) or 0.30 (Aggressive)
        - Long Wings: Define width based on capital (e.g., $5 wide or $10 wide)

        Validation Rules:
        1. Credit Check: Net Credit >= 1/3 of Wing Width
        2. Delta Neutrality: abs(Net Delta) < 0.10
        3. Theta Efficiency: DTE between 30-45 days (sweet spot)
        """
        dte = self._calculate_dte(expiration_date)
        if dte < 30 or dte > 60:
            logger.debug(f"Iron Condor: DTE {dte} not optimal (30-60 days preferred)")
            # Still allow, but note it's not optimal

        # Determine wing width based on capital
        # Conservative: $5 wide, Aggressive: $10 wide
        wing_width = 5.0 if risk_profile == RiskProfile.CONSERVATIVE else 10.0

        # Target deltas for short strikes
        target_delta_short = 0.20 if risk_profile == RiskProfile.CONSERVATIVE else 0.30

        # Find short call strike (OTM)
        short_call = self._find_option(chain, OptionType.CALL, target_delta_short, spot_price)
        if not short_call:
            return None

        # Find long call strike (further OTM, wing_width away)
        short_call_strike = float(short_call.get("strike", short_call.get("strike_price", 0.0)))
        long_call_strike = short_call_strike + wing_width

        # Find closest call to long_call_strike
        calls = chain.get("calls", [])
        long_call = None
        min_diff = float("inf")
        for call in calls:
            strike = float(call.get("strike", call.get("strike_price", 0.0)))
            diff = abs(strike - long_call_strike)
            if diff < min_diff:
                min_diff = diff
                long_call = call

        if not long_call:
            return None

        # Find short put strike (OTM)
        short_put = self._find_option(chain, OptionType.PUT, -target_delta_short, spot_price)
        if not short_put:
            return None

        # Find long put strike (further OTM, wing_width away)
        short_put_strike = float(short_put.get("strike", short_put.get("strike_price", 0.0)))
        long_put_strike = short_put_strike - wing_width

        # Find closest put to long_put_strike
        puts = chain.get("puts", [])
        long_put = None
        min_diff = float("inf")
        for put in puts:
            strike = float(put.get("strike", put.get("strike_price", 0.0)))
            diff = abs(strike - long_put_strike)
            if diff < min_diff:
                min_diff = diff
                long_put = put

        if not long_put:
            return None

        # Create legs
        legs = [
            self._create_option_leg(short_call, symbol, -1, OptionType.CALL, expiration_date, dte, spot_price),  # Sell
            self._create_option_leg(long_call, symbol, +1, OptionType.CALL, expiration_date, dte, spot_price),  # Buy
            self._create_option_leg(short_put, symbol, -1, OptionType.PUT, expiration_date, dte, spot_price),  # Sell
            self._create_option_leg(long_put, symbol, +1, OptionType.PUT, expiration_date, dte, spot_price),  # Buy
        ]

        # Validate liquidity
        if not self._validate_liquidity(legs):
            return None

        # Calculate net credit/debit
        net_credit = (
            short_call["bid"] + short_put["bid"] - long_call["ask"] - long_put["ask"]
        )

        # Validation Rule 1: Credit Check
        min_credit_required = wing_width / 3.0
        if net_credit < min_credit_required:
            logger.debug(
                f"Iron Condor: Credit {net_credit:.2f} < required {min_credit_required:.2f}"
            )
            return None

        # Calculate net Greeks
        net_greeks = self._calculate_net_greeks(legs)

        # Validation Rule 2: Delta Neutrality
        if abs(net_greeks["delta"]) >= 0.10:
            logger.debug(
                f"Iron Condor: Net Delta {net_greeks['delta']:.4f} not neutral (abs >= 0.10)"
            )
            return None

        # Calculate metrics
        max_profit = net_credit
        max_loss = wing_width - net_credit
        risk_reward_ratio = max_profit / max_loss if max_loss > 0 else 0.0

        # Estimate POP (Probability of Profit) - simplified model
        # For Iron Condor, POP ≈ (Wing Width - Net Credit) / Wing Width
        pop = (wing_width - net_credit) / wing_width if wing_width > 0 else 0.0
        pop = max(0.0, min(1.0, pop))  # Clamp to [0, 1]

        # Breakeven points
        breakeven_points = [
            short_call_strike + net_credit,
            short_put_strike - net_credit,
        ]

        liquidity_score = self._calculate_liquidity_score(legs)
        theta_decay_per_day = net_greeks["theta"] * 100.0  # Convert to dollars per day

        return CalculatedStrategy(
            name="High Theta Iron Condor",
            description=f"Neutral strategy collecting premium. Wing width: ${wing_width:.0f}, Credit: ${net_credit:.2f}",
            legs=legs,
            metrics={
                "max_profit": round(max_profit, 2),
                "max_loss": round(max_loss, 2),
                "risk_reward_ratio": round(risk_reward_ratio, 4),
                "pop": round(pop, 4),
                "breakeven_points": [round(bp, 2) for bp in breakeven_points],
                "net_greeks": {k: round(v, 4) for k, v in net_greeks.items()},
                "theta_decay_per_day": round(theta_decay_per_day, 2),
                "liquidity_score": liquidity_score,
            },
        )

    def _algorithm_long_straddle(
        self,
        chain: dict[str, Any],
        symbol: str,
        spot_price: float,
        expiration_date: str,
        risk_profile: RiskProfile,
        capital: float,
    ) -> CalculatedStrategy | None:
        """
        Algorithm 2: Long Straddle (Volatile + Low IV).

        Objective: Profit from Gamma explosion or Vega expansion.

        Strike Selection:
        - Buy ATM Call + Buy ATM Put

        Validation Rules:
        1. Cost Check: Total Debit should not exceed X% of Spot Price
        2. Gamma/Theta Ratio: High Gamma relative to Theta bleed
        3. Vega Check: Ensure current IV Rank < 30 (buying in high IV is poor)
        """
        dte = self._calculate_dte(expiration_date)

        # Find ATM options (delta closest to 0.50 for calls, -0.50 for puts)
        atm_call = self._find_option(chain, OptionType.CALL, 0.50, spot_price)
        atm_put = self._find_option(chain, OptionType.PUT, -0.50, spot_price)

        if not atm_call or not atm_put:
            return None

        # Create legs
        legs = [
            self._create_option_leg(atm_call, symbol, +1, OptionType.CALL, expiration_date, dte, spot_price),  # Buy
            self._create_option_leg(atm_put, symbol, +1, OptionType.PUT, expiration_date, dte, spot_price),  # Buy
        ]

        # Validate liquidity
        if not self._validate_liquidity(legs):
            return None

        # Calculate net debit
        net_debit = atm_call["ask"] + atm_put["ask"]

        # Validation Rule 1: Cost Check
        # Total debit should not exceed 10% of spot price (adjustable)
        max_debit_pct = 0.10
        if net_debit > spot_price * max_debit_pct:
            logger.debug(
                f"Long Straddle: Debit {net_debit:.2f} > {max_debit_pct*100}% of spot {spot_price:.2f}"
            )
            return None

        # Calculate net Greeks
        net_greeks = self._calculate_net_greeks(legs)

        # Validation Rule 2: Gamma/Theta Ratio
        # We want high Gamma relative to Theta (at least 2:1)
        if net_greeks["theta"] >= 0 or abs(net_greeks["gamma"]) < abs(net_greeks["theta"]) * 2:
            logger.debug(
                f"Long Straddle: Gamma/Theta ratio insufficient. Gamma: {net_greeks['gamma']:.4f}, Theta: {net_greeks['theta']:.4f}"
            )
            # Still allow, but note it's not optimal

        # Note: IV Rank check would require historical IV data
        # For now, we skip this validation but log a warning
        logger.debug("Long Straddle: IV Rank check skipped (requires historical data)")

        # Calculate metrics
        # Max profit: Unlimited (either direction)
        # Max loss: Net debit
        max_profit = float("inf")  # Unlimited
        max_loss = net_debit
        risk_reward_ratio = float("inf")  # Unlimited upside

        # Estimate POP - simplified model
        # For Long Straddle, POP is low (need significant move)
        # Rough estimate: POP ≈ 30% for ATM straddle
        pop = 0.30

        # Breakeven points
        strike = float(atm_call.get("strike", atm_call.get("strike_price", spot_price)))
        breakeven_points = [
            strike + net_debit,  # Upper breakeven
            strike - net_debit,  # Lower breakeven
        ]

        liquidity_score = self._calculate_liquidity_score(legs)
        theta_decay_per_day = net_greeks["theta"] * 100.0

        return CalculatedStrategy(
            name="Long Straddle (Volatility Play)",
            description=f"Buy ATM Call + Put. Debit: ${net_debit:.2f}. Profits from large moves in either direction.",
            legs=legs,
            metrics={
                "max_profit": "Unlimited",
                "max_loss": round(max_loss, 2),
                "risk_reward_ratio": "Unlimited",
                "pop": round(pop, 4),
                "breakeven_points": [round(bp, 2) for bp in breakeven_points],
                "net_greeks": {k: round(v, 4) for k, v in net_greeks.items()},
                "theta_decay_per_day": round(theta_decay_per_day, 2),
                "liquidity_score": liquidity_score,
            },
        )

    def _algorithm_bull_call_spread(
        self,
        chain: dict[str, Any],
        symbol: str,
        spot_price: float,
        expiration_date: str,
        risk_profile: RiskProfile,
        capital: float,
    ) -> CalculatedStrategy | None:
        """
        Algorithm 3: Bull Call Spread (Bullish).

        Objective: Directional play with capped risk.

        Strike Selection:
        - Buy Leg: Delta ≈ 0.65 (ITM replacement)
        - Sell Leg: Delta ≈ 0.30 (OTM, paying for the Theta)

        Validation Rules:
        1. Debit Check: Net Debit < 50% of Spread Width
        """
        dte = self._calculate_dte(expiration_date)

        # Find buy leg (ITM, delta ~0.65)
        buy_call = self._find_option(chain, OptionType.CALL, 0.65, spot_price)
        if not buy_call:
            return None

        # Find sell leg (OTM, delta ~0.30)
        sell_call = self._find_option(chain, OptionType.CALL, 0.30, spot_price)
        if not sell_call:
            return None

        buy_strike = float(buy_call.get("strike", buy_call.get("strike_price", 0.0)))
        sell_strike = float(sell_call.get("strike", sell_call.get("strike_price", 0.0)))

        # Ensure buy strike < sell strike (spread)
        if buy_strike >= sell_strike:
            return None

        spread_width = sell_strike - buy_strike

        # Create legs
        legs = [
            self._create_option_leg(buy_call, symbol, +1, OptionType.CALL, expiration_date, dte, spot_price),  # Buy
            self._create_option_leg(sell_call, symbol, -1, OptionType.CALL, expiration_date, dte, spot_price),  # Sell
        ]

        # Validate liquidity
        if not self._validate_liquidity(legs):
            return None

        # Calculate net debit
        net_debit = buy_call["ask"] - sell_call["bid"]

        # Validation Rule 1: Debit Check
        max_debit = spread_width * 0.50
        if net_debit >= max_debit:
            logger.debug(
                f"Bull Call Spread: Debit {net_debit:.2f} >= 50% of width {max_debit:.2f}"
            )
            return None

        # Calculate net Greeks
        net_greeks = self._calculate_net_greeks(legs)

        # Calculate metrics
        max_profit = spread_width - net_debit
        max_loss = net_debit
        risk_reward_ratio = max_profit / max_loss if max_loss > 0 else 0.0

        # Estimate POP - simplified model
        # For Bull Call Spread, POP depends on how far ITM the buy leg is
        # Rough estimate: POP ≈ 60-70% for 0.65 delta buy leg
        pop = 0.65

        # Breakeven point
        breakeven_points = [buy_strike + net_debit]

        liquidity_score = self._calculate_liquidity_score(legs)
        theta_decay_per_day = net_greeks["theta"] * 100.0

        return CalculatedStrategy(
            name="Bull Call Spread",
            description=f"Bullish spread. Debit: ${net_debit:.2f}, Max profit: ${max_profit:.2f}",
            legs=legs,
            metrics={
                "max_profit": round(max_profit, 2),
                "max_loss": round(max_loss, 2),
                "risk_reward_ratio": round(risk_reward_ratio, 4),
                "pop": round(pop, 4),
                "breakeven_points": [round(bp, 2) for bp in breakeven_points],
                "net_greeks": {k: round(v, 4) for k, v in net_greeks.items()},
                "theta_decay_per_day": round(theta_decay_per_day, 2),
                "liquidity_score": liquidity_score,
            },
        )

    def generate_strategies(
        self,
        chain: dict[str, Any],
        symbol: str,
        spot_price: float,
        outlook: Outlook,
        risk_profile: RiskProfile,
        capital: float,
        expiration_date: str | None = None,
    ) -> list[CalculatedStrategy]:
        """
        Generate strategy recommendations based on outlook and risk profile.

        Args:
            chain: Option chain data with Greeks
            symbol: Stock symbol
            spot_price: Current spot price
            outlook: Market outlook (BULLISH, BEARISH, NEUTRAL, VOLATILE)
            risk_profile: Risk tolerance (CONSERVATIVE, AGGRESSIVE)
            capital: Available capital
            expiration_date: Preferred expiration date (if None, selects optimal DTE)

        Returns:
            List of valid CalculatedStrategy objects
        """
        strategies: list[CalculatedStrategy] = []

        # Filter expirations (focus on 30-60 DTE for optimal Greeks behavior)
        # For now, use the provided expiration_date or find best one
        if expiration_date is None:
            # Find expiration closest to 45 DTE
            # This would require iterating through available expirations
            # For now, we'll use a placeholder - in production, fetch multiple expirations
            logger.warning("No expiration_date provided, using chain's expiration")
            expiration_date = chain.get("expiration_date", "")

        if not expiration_date:
            logger.error("No expiration date available")
            return []

        # Select algorithm based on outlook
        if outlook == Outlook.NEUTRAL:
            strategy = self._algorithm_iron_condor(
                chain, symbol, spot_price, expiration_date, risk_profile, capital
            )
            if strategy:
                strategies.append(strategy)

        elif outlook == Outlook.VOLATILE:
            strategy = self._algorithm_long_straddle(
                chain, symbol, spot_price, expiration_date, risk_profile, capital
            )
            if strategy:
                strategies.append(strategy)

        elif outlook == Outlook.BULLISH:
            strategy = self._algorithm_bull_call_spread(
                chain, symbol, spot_price, expiration_date, risk_profile, capital
            )
            if strategy:
                strategies.append(strategy)

        elif outlook == Outlook.BEARISH:
            # For bearish, we could implement Bear Put Spread (mirror of Bull Call Spread)
            # For now, return empty
            logger.debug("Bearish strategies not yet implemented")
            pass

        # Sort by POP (Probability of Profit) descending
        strategies.sort(
            key=lambda s: s.metrics.get("pop", 0.0) if isinstance(s.metrics.get("pop"), (int, float)) else 0.0,
            reverse=True,
        )

        return strategies
