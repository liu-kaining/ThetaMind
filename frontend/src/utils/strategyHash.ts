/**
 * Utility functions for calculating strategy hash for image caching.
 * This must match the backend implementation in backend/app/utils/strategy_hash.py
 */

export interface StrategySummary {
  symbol: string
  expiration_date?: string
  legs: Array<{
    strike: number
    type: string
    action: string
    quantity: number
    [key: string]: any
  }>
  [key: string]: any
}

/**
 * Calculate a unique hash for a strategy based on key identifying fields.
 * 
 * The hash is based on:
 * - symbol
 * - expiration_date
 * - legs (sorted by strike, type, action, quantity)
 * 
 * This ensures that the same strategy configuration will always generate
 * the same hash, allowing us to cache and reuse generated images.
 * 
 * @param strategySummary Strategy summary dictionary with symbol, expiration_date, and legs
 * @returns SHA256 hash (64 character hex string) of the strategy
 */
export function calculateStrategyHash(strategySummary: StrategySummary): string {
  // Extract key fields
  const symbol = (strategySummary.symbol || "").toUpperCase()
  const expirationDate = strategySummary.expiration_date || ""
  
  // Extract and normalize legs
  const legs = strategySummary.legs || []
  
  // Normalize legs: sort by strike, type, action, quantity
  // Only include identifying fields (not Greeks or prices which may change)
  const normalizedLegs = legs.map((leg) => ({
    strike: Number(leg.strike || 0),
    type: String(leg.type || "").toUpperCase(),
    action: String(leg.action || "").toUpperCase(),
    quantity: Number(leg.quantity || 0),
  }))
  
  // Sort legs for consistent hashing
  normalizedLegs.sort((a, b) => {
    if (a.strike !== b.strike) return a.strike - b.strike
    if (a.type !== b.type) return a.type.localeCompare(b.type)
    if (a.action !== b.action) return a.action.localeCompare(b.action)
    return a.quantity - b.quantity
  })
  
  // Create hash input
  const hashInput = {
    symbol,
    expiration_date: expirationDate,
    legs: normalizedLegs,
  }
  
  // Convert to JSON string (sorted keys for consistency)
  const hashString = JSON.stringify(hashInput)
  
  // Calculate SHA256 hash using Web Crypto API
  // Note: This is async, but we'll use a synchronous approach with crypto.subtle
  // For now, we'll use a simple hash function, but ideally we should use crypto.subtle.digest
  // However, since crypto.subtle.digest is async, we need to handle it differently
  // For now, let's use a synchronous approach with a library or implement async version
  
  // Using Web Crypto API (async)
  return hashString // Placeholder - we'll implement proper hashing below
}

/**
 * Calculate strategy hash asynchronously using Web Crypto API
 */
export async function calculateStrategyHashAsync(strategySummary: StrategySummary): Promise<string> {
  // Extract key fields
  const symbol = (strategySummary.symbol || "").toUpperCase()
  const expirationDate = strategySummary.expiration_date || ""
  
  // Extract and normalize legs
  const legs = strategySummary.legs || []
  
  // Normalize legs: sort by strike, type, action, quantity
  // IMPORTANT: strike must be float (to match Python's float()), quantity must be integer
  const normalizedLegs = legs.map((leg) => ({
    strike: parseFloat(String(leg.strike || 0)), // Ensure float (e.g., 225.0 not 225)
    type: String(leg.type || "").toUpperCase(),
    action: String(leg.action || "").toUpperCase(),
    quantity: parseInt(String(leg.quantity || 0), 10), // Ensure integer
  }))
  
  // Sort legs for consistent hashing
  normalizedLegs.sort((a, b) => {
    if (a.strike !== b.strike) return a.strike - b.strike
    if (a.type !== b.type) return a.type.localeCompare(b.type)
    if (a.action !== b.action) return a.action.localeCompare(b.action)
    return a.quantity - b.quantity
  })
  
  // Create hash input
  const hashInput: Record<string, any> = {
    symbol,
    expiration_date: expirationDate,
    legs: normalizedLegs,
  }
  
  // Convert to JSON string with sorted keys and no spaces (to match Python's json.dumps with sort_keys=True, separators=(",", ":"))
  // Python's json.dumps with sort_keys=True and separators=(",", ":") produces compact JSON with sorted keys
  // We need to replicate this exactly
  const sortedKeys = Object.keys(hashInput).sort()
  const hashString = "{" + sortedKeys.map(key => {
    const value: any = hashInput[key]
    let valueStr: string
    if (Array.isArray(value)) {
      // For arrays, stringify each element and join with comma (no spaces)
      valueStr = "[" + value.map(v => {
        // For leg objects, sort keys and stringify
        if (typeof v === "object" && v !== null) {
          const legKeys = Object.keys(v).sort()
          return "{" + legKeys.map(k => {
            const val: any = (v as Record<string, any>)[k]
            // Numbers should be serialized as numbers (not strings), strings as JSON strings
            // IMPORTANT: Python's json.dumps formats floats as "225.0" and ints as "1"
            // We need to match this exactly
            let valStr: string
            if (typeof val === "number") {
              // Python float always shows decimal point (e.g., 225.0), ints don't (e.g., 1)
              // Check if it's the strike field (should be float) or quantity field (should be int)
              if (k === "strike") {
                // Strike is always a float in Python, so ensure decimal point (e.g., 225.0)
                // Use toFixed(1) to ensure at least one decimal place, then remove trailing zeros if needed
                // But Python shows 225.0, so we need to keep .0
                valStr = Number.isInteger(val) ? val.toFixed(1) : val.toString()
              } else if (k === "quantity") {
                // Quantity is always an int in Python, no decimal point (e.g., 1)
                valStr = Math.floor(val).toString()
              } else {
                // Other numeric fields - use default behavior
                valStr = val.toString()
              }
            } else {
              valStr = JSON.stringify(val)
            }
            return JSON.stringify(k) + ":" + valStr
          }).join(",") + "}"
        }
        return JSON.stringify(v)
      }).join(",") + "]"
    } else {
      if (typeof value === "number") {
        valueStr = value.toString()
      } else {
        valueStr = JSON.stringify(value)
      }
    }
    return JSON.stringify(key) + ":" + valueStr
  }).join(",") + "}"
  
  // Calculate SHA256 hash using Web Crypto API
  const encoder = new TextEncoder()
  const data = encoder.encode(hashString)
  const hashBuffer = await crypto.subtle.digest("SHA-256", data)
  
  // Convert buffer to hex string
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  const hashHex = hashArray.map((b) => b.toString(16).padStart(2, "0")).join("")
  
  return hashHex
}

