"""Utility functions for calculating strategy hash for image caching."""

import hashlib
import json
from typing import Any


def calculate_strategy_hash(strategy_summary: dict[str, Any]) -> str:
    """
    Calculate a unique hash for a strategy based on key identifying fields.
    
    The hash is based on:
    - symbol
    - expiration_date
    - legs (sorted by strike, type, action, quantity)
    
    This ensures that the same strategy configuration will always generate
    the same hash, allowing us to cache and reuse generated images.
    
    Args:
        strategy_summary: Strategy summary dictionary with symbol, expiration_date, and legs
        
    Returns:
        SHA256 hash (64 character hex string) of the strategy
    """
    # Extract key fields
    symbol = strategy_summary.get("symbol", "").upper()
    expiration_date = strategy_summary.get("expiration_date", "")
    
    # Extract and normalize legs
    legs = strategy_summary.get("legs", [])
    
    # Normalize legs: sort by strike, type, action, quantity
    # Only include identifying fields (not Greeks or prices which may change)
    normalized_legs = []
    for leg in legs:
        normalized_leg = {
            "strike": float(leg.get("strike", 0)),
            "type": str(leg.get("type", "")).upper(),
            "action": str(leg.get("action", "")).upper(),
            "quantity": int(leg.get("quantity", 0)),
        }
        normalized_legs.append(normalized_leg)
    
    # Sort legs for consistent hashing
    normalized_legs.sort(key=lambda x: (x["strike"], x["type"], x["action"], x["quantity"]))
    
    # Create hash input
    hash_input = {
        "symbol": symbol,
        "expiration_date": expiration_date,
        "legs": normalized_legs,
    }
    
    # Convert to JSON string (sorted keys for consistency)
    hash_string = json.dumps(hash_input, sort_keys=True, separators=(",", ":"))
    
    # Calculate SHA256 hash
    hash_obj = hashlib.sha256(hash_string.encode("utf-8"))
    return hash_obj.hexdigest()

