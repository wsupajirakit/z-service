// Locale-aware formatting. The wall clock follows the server timezone setting
// (offset in minutes), not the browser zone, to match the legacy UI and Telegram messages.
export type DisplayZone = { offset_minutes: number; label: string }

export function parseTimestamp(value: string | null | undefined): Date | null {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatDateTime(
  value: string | null | undefined,
  locale: string,
  zone: DisplayZone | null,
): string {
  const date = parseTimestamp(value)
  if (!date) return value ?? ''
  const shifted = new Date(date.getTime() + (zone?.offset_minutes ?? 0) * 60_000)
  const text = new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: zone ? 'UTC' : undefined,
  }).format(zone ? shifted : date)
  return zone ? `${text} (${zone.label})` : text
}

export function formatNumber(value: unknown, locale: string, digits = 2): string {
  const num = typeof value === 'string' ? Number(value) : value
  if (typeof num !== 'number' || !Number.isFinite(num)) return value == null ? '' : String(value)
  return new Intl.NumberFormat(locale, { maximumFractionDigits: digits }).format(num)
}

/** Renders any JSON cell value as plain text (never HTML). */
export function cellText(value: unknown, locale: string): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'number') return formatNumber(value, locale, 4)
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
