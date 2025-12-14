"""Daily Picks Service - Orchestrates the complete daily picks generation pipeline."""

import json
import logging
import re
from datetime import date, datetime, timedelta
from typing import Any

import pytz

from app.schemas.strategy_recommendation import Outlook, RiskProfile
from app.services.ai_service import ai_service
from app.services.market_scanner import get_hot_options_stocks
from app.services.strategy_engine import StrategyEngine
from app.services.tiger_service import tiger_service

logger = logging.getLogger(__name__)

EST = pytz.timezone("US/Eastern")


async def generate_daily_picks_pipeline() -> list[dict[str, Any]]:
    """
    Generate daily picks using a 4-step pipeline:
    
    1. Scan: Get Top 10 hot option stocks
    2. Quant Strategy: Generate strategies for each stock, select best based on Risk/Reward
    3. AI Narrative: Generate AI commentary for Top 3 winners
    4. Return formatted picks list
    
    Returns:
        List of daily pick dicts with symbol, strategy, AI commentary, etc.
    """
    logger.info("🚀 Starting Daily Picks Pipeline...")
    
    # ========== STEP 1: MARKET SCAN ==========
    logger.info("Step 1: Scanning hot option stocks...")
    hot_stocks = await get_hot_options_stocks(limit=10)
    logger.info(f"Found {len(hot_stocks)} hot stocks: {hot_stocks}")
    
    if not hot_stocks:
        raise ValueError("No hot stocks found from market scanner")
    
    # ========== STEP 2: QUANT STRATEGY GENERATION ==========
    logger.info("Step 2: Generating strategies for each stock...")
    engine = StrategyEngine()
    
    # Calculate next Friday expiration (common weekly expiration)
    today_est = datetime.now(EST).date()
    days_until_friday = (4 - today_est.weekday()) % 7
    if days_until_friday == 0:
        days_until_friday = 7  # If today is Friday, use next Friday
    expiration_date = (today_est + timedelta(days=days_until_friday)).strftime("%Y-%m-%d")
    
    all_strategies: list[dict[str, Any]] = []
    
    for symbol in hot_stocks:
        try:
            # Fetch option chain
            chain_data = await tiger_service.get_option_chain(
                symbol=symbol,
                expiration_date=expiration_date,
                is_pro=True,  # Use pro data for daily picks generation
            )
            
            spot_price = chain_data.get("spot_price") or chain_data.get("underlying_price")
            if not spot_price or spot_price <= 0:
                logger.warning(f"No spot price for {symbol}, skipping")
                continue
            
            # Generate strategies for different outlooks and risk profiles
            # Try multiple combinations to find the best strategy
            best_strategy = None
            best_score = -float("inf")
            
            outlooks_to_try = [Outlook.BULLISH, Outlook.NEUTRAL, Outlook.VOLATILE]
            risk_profiles_to_try = [RiskProfile.CONSERVATIVE, RiskProfile.AGGRESSIVE]
            capital = 10000.0  # Assume $10k capital for strategy generation
            
            for outlook in outlooks_to_try:
                for risk_profile in risk_profiles_to_try:
                    try:
                        strategies = engine.generate_strategies(
                            chain=chain_data,
                            symbol=symbol,
                            spot_price=float(spot_price),
                            outlook=outlook,
                            risk_profile=risk_profile,
                            capital=capital,
                            expiration_date=expiration_date,
                        )
                        
                        # Score strategies by Risk/Reward ratio
                        for strategy in strategies:
                            max_profit = strategy.max_profit or 0
                            max_loss = abs(strategy.max_loss or 0)
                            
                            if max_loss > 0:
                                risk_reward_ratio = max_profit / max_loss
                            else:
                                risk_reward_ratio = float("inf") if max_profit > 0 else 0
                            
                            # Combined score: risk/reward ratio + profit magnitude
                            score = risk_reward_ratio * 0.7 + (max_profit / 1000) * 0.3
                            
                            if score > best_score:
                                best_score = score
                                best_strategy = {
                                    "symbol": symbol,
                                    "strategy": strategy.dict() if hasattr(strategy, 'dict') else strategy.model_dump(),
                                    "outlook": outlook.value,
                                    "risk_profile": risk_profile.value,
                                    "score": score,
                                    "risk_reward_ratio": risk_reward_ratio,
                                }
                    except Exception as e:
                        logger.warning(f"Failed to generate strategy for {symbol} ({outlook.value}, {risk_profile.value}): {e}")
                        continue
            
            if best_strategy:
                all_strategies.append(best_strategy)
                logger.info(f"✓ Best strategy for {symbol}: {best_strategy['strategy'].get('strategy_type', 'N/A')} (score: {best_score:.2f})")
            else:
                logger.warning(f"No valid strategies found for {symbol}")
                
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}", exc_info=True)
            continue
    
    if not all_strategies:
        raise ValueError("No strategies generated for any stocks")
    
    # Sort by score and take top 3
    all_strategies.sort(key=lambda x: x["score"], reverse=True)
    top_3_strategies = all_strategies[:3]
    
    logger.info(f"✓ Selected top 3 strategies from {len(all_strategies)} candidates")
    
    # ========== STEP 3: AI NARRATIVE GENERATION ==========
    logger.info("Step 3: Generating AI commentary for top 3 picks...")
    
    picks_with_ai: list[dict[str, Any]] = []
    
    for idx, pick_data in enumerate(top_3_strategies, 1):
        symbol = pick_data["symbol"]
        strategy_data = pick_data["strategy"]
        
        try:
            # Generate AI commentary
            # Format strategy data for AI
            strategy_for_ai = {
                "symbol": symbol,
                "strategy_type": strategy_data.get("strategy_type", "N/A"),
                "legs": strategy_data.get("legs", []),
                "max_profit": strategy_data.get("max_profit", 0),
                "max_loss": strategy_data.get("max_loss", 0),
                "breakeven": strategy_data.get("breakeven", []),
                "outlook": pick_data["outlook"],
                "risk_profile": pick_data["risk_profile"],
            }
            
            # Get option chain for AI context (filtered)
            chain_data = await tiger_service.get_option_chain(
                symbol=symbol,
                expiration_date=expiration_date,
                is_pro=True,
            )
            
            # Generate AI narrative using a specialized prompt
            commentary_prompt = f"""Generate a concise investment commentary for this option strategy pick.

**Strategy:**
- Symbol: {symbol}
- Type: {strategy_data.get('strategy_type', 'N/A')}
- Outlook: {pick_data['outlook']}
- Risk Profile: {pick_data['risk_profile']}
- Max Profit: ${strategy_data.get('max_profit', 0):,.2f}
- Max Loss: ${abs(strategy_data.get('max_loss', 0)):,.2f}
- Breakeven: {strategy_data.get('breakeven', [])}

**Requirements:**
Return a JSON object with:
{{
  "headline": "Brief headline (max 100 chars)",
  "analysis": "2-3 sentence analysis of why this strategy makes sense",
  "risks": "Key risks to watch (1-2 sentences)",
  "target_price": "Target price or price range",
  "timeframe": "Recommended holding period"
}}

Return ONLY valid JSON, no markdown or other text."""

            # Use AI service to generate commentary
            # For now, we'll use generate_report and parse JSON from it
            # In future, we can create a dedicated method for structured JSON output
            ai_response = await ai_service.generate_report(
                strategy_data=strategy_for_ai,
                option_chain=chain_data,
            )
            
            # Extract JSON from AI response (handle markdown code fences)
            # Try to extract JSON from response
            json_match = re.search(r'\{[^{}]*"headline"[^{}]*\}', ai_response, re.DOTALL)
            if json_match:
                try:
                    commentary = json.loads(json_match.group())
                except json.JSONDecodeError:
                    # Fallback: create basic commentary
                    commentary = {
                        "headline": f"{symbol} {strategy_data.get('strategy_type', 'Strategy')} Opportunity",
                        "analysis": ai_response[:200] if len(ai_response) > 200 else ai_response,
                        "risks": "Monitor position size and market conditions",
                        "target_price": "See strategy breakeven points",
                        "timeframe": "Until expiration",
                    }
            else:
                # Fallback: create basic commentary from AI response
                commentary = {
                    "headline": f"{symbol} {strategy_data.get('strategy_type', 'Strategy')} Opportunity",
                    "analysis": ai_response[:300] if len(ai_response) > 300 else ai_response,
                    "risks": "Monitor position size and market conditions",
                    "target_price": "See strategy breakeven points",
                    "timeframe": "Until expiration",
                }
            
            # Combine strategy with AI commentary
            pick = {
                "symbol": symbol,
                "strategy_type": strategy_data.get("strategy_type", "N/A"),
                "strategy": strategy_data,
                "outlook": pick_data["outlook"],
                "risk_level": pick_data["risk_profile"],
                "headline": commentary.get("headline", f"{symbol} Strategy Pick"),
                "analysis": commentary.get("analysis", ""),
                "risks": commentary.get("risks", ""),
                "target_price": commentary.get("target_price", ""),
                "timeframe": commentary.get("timeframe", ""),
                "max_profit": strategy_data.get("max_profit", 0),
                "max_loss": strategy_data.get("max_loss", 0),
                "breakeven": strategy_data.get("breakeven", []),
            }
            
            picks_with_ai.append(pick)
            logger.info(f"✓ Generated AI commentary for {symbol}")
            
        except Exception as e:
            logger.error(f"Failed to generate AI commentary for {symbol}: {e}", exc_info=True)
            # Include pick without AI commentary
            picks_with_ai.append({
                "symbol": pick_data["symbol"],
                "strategy_type": strategy_data.get("strategy_type", "N/A"),
                "strategy": strategy_data,
                "outlook": pick_data["outlook"],
                "risk_level": pick_data["risk_profile"],
                "headline": f"{pick_data['symbol']} Strategy Pick",
                "analysis": "Strategy analysis pending",
                "risks": "Standard option strategy risks apply",
                "target_price": "",
                "timeframe": "Until expiration",
                "max_profit": strategy_data.get("max_profit", 0),
                "max_loss": strategy_data.get("max_loss", 0),
                "breakeven": strategy_data.get("breakeven", []),
            })
    
    logger.info(f"✅ Daily Picks Pipeline completed. Generated {len(picks_with_ai)} picks.")
    return picks_with_ai

