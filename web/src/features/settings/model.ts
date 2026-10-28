// Pure settings logic: timezone label, validation against the backend ranges.
import { domainConfig } from '../../config/domain.ts'
import { intInRange } from '../../utils/validate.ts'

const { timezoneOffsetMinutes: tzRange, autoSkipMinutes } = domainConfig.limits

/** "UTC+7", "UTC-3:30", "UTC+0" from an offset in minutes (east of UTC is positive). */
export function utcLabel(offset: number): string {
  const sign = offset < 0 ? '-' : '+'
  const abs = Math.abs(offset)
  const h = Math.floor(abs / 60)
  const mins = abs % 60
  return `UTC${sign}${h}${mins ? `:${String(mins).padStart(2, '0')}` : ''}`
}

export function parseTimezone(offsetRaw: string, labelRaw: string):
  { offset: number; label: string } | null {
  const offset = intInRange(offsetRaw, tzRange.min, tzRange.max)
  if (offset === null) return null
  return { offset, label: labelRaw.trim() || utcLabel(offset) }
}

export const parseAutoSkip = (raw: string) =>
  intInRange(raw, autoSkipMinutes.min, autoSkipMinutes.max)

/** The browser's current zone, for the "use my zone" shortcut. */
export function browserZone(now = new Date()): { offset: number; label: string } {
  const offset = -now.getTimezoneOffset()
  const zone = Intl.DateTimeFormat().resolvedOptions().timeZone
  return { offset, label: `${zone} (${utcLabel(offset)})` }
}
