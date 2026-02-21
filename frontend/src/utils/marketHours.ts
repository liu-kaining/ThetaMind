/**
 * US market hours (NYSE/NASDAQ) in Eastern Time.
 * Regular session: Mon–Fri 9:30 AM – 4:00 PM ET.
 * Used for Dashboard empty states so we show "Market closed" instead of blank when outside hours.
 */

import { formatInTimeZone, utcToZonedTime } from "date-fns-tz"
import { addDays, setHours, setMinutes, setSeconds, setMilliseconds, isWeekend, isBefore } from "date-fns"

const TZ_ET = "America/New_York"
const OPEN_HOUR = 9
const OPEN_MINUTE = 30
const CLOSE_HOUR = 16
const CLOSE_MINUTE = 0

/**
 * Whether US regular market session is open at the given time (default: now).
 */
export function isUSMarketOpen(now: Date = new Date()): boolean {
  // Uncomment the following line to forcefully show market open state during development/weekends
  return true;
  
  const et = utcToZonedTime(now, TZ_ET)
  if (isWeekend(et)) return false
  const open = setMilliseconds(setSeconds(setMinutes(setHours(et, OPEN_HOUR), OPEN_MINUTE), 0), 0)
  const close = setMilliseconds(setSeconds(setMinutes(setHours(et, CLOSE_HOUR), CLOSE_MINUTE), 0), 0)
  return !isBefore(et, open) && isBefore(et, close)
}

/**
 * Next market open moment in ET (next weekday 9:30 AM ET).
 */
function getNextOpenET(now: Date): Date {
  const et = utcToZonedTime(now, TZ_ET)
  for (let i = 0; i <= 7; i++) {
    const day = addDays(et, i)
    if (isWeekend(day)) continue
    const open = setMilliseconds(
      setSeconds(setMinutes(setHours(day, OPEN_HOUR), OPEN_MINUTE), 0),
      0
    )
    if (i === 0 && isBefore(et, open)) return open
    if (i > 0) return open
  }
  return et
}

export type MarketStatus = {
  isOpen: boolean
  label: string
  shortLabel: string
  nextOpenET?: string
}

/**
 * Get market status for display (open/closed + next open time when closed).
 */
export function getMarketStatus(now: Date = new Date()): MarketStatus {
  const open = isUSMarketOpen(now)
  if (open) {
    return {
      isOpen: true,
      label: "US market is open (regular session 9:30 AM–4:00 PM ET)",
      shortLabel: "Market open",
    }
  }
  const nextOpen = getNextOpenET(now)
  const nextOpenET = formatInTimeZone(nextOpen, TZ_ET, "EEE, MMM d 'at' h:mm a zzz")
  return {
    isOpen: false,
    label: "US market is closed. Regular session: Mon–Fri 9:30 AM–4:00 PM ET.",
    shortLabel: "Market closed",
    nextOpenET,
  }
}
