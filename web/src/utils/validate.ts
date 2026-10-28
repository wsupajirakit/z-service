// Input checks shared by write forms. They mirror backend limits so bad input never leaves
// the browser; the server still validates everything.
const SYMBOL = /^[A-Z0-9][A-Z0-9.!_-]{0,29}$/
const NAME_MAX = 60

/** Upper-cased ticker or null. No '/' (it is a path segment in DELETE routes). */
export function cleanSymbol(raw: string): string | null {
  const s = raw.trim().toUpperCase()
  return SYMBOL.test(s) ? s : null
}

/** Exchange codes are upper-case letters/digits, e.g. NASDAQ; empty means unknown. */
export function cleanExchange(raw: string): string | null {
  const s = raw.trim().toUpperCase()
  return /^[A-Z0-9_]{1,20}$/.test(s) ? s : null
}

/** List or portfolio name: trimmed, 1..60 chars, no '/'. */
export function cleanName(raw: string): string | null {
  const s = raw.trim()
  return s.length > 0 && s.length <= NAME_MAX && !s.includes('/') ? s : null
}

/** Integer within [min, max] or null. */
export function intInRange(raw: string | number, min: number, max: number): number | null {
  const n = typeof raw === 'number' ? raw : raw.trim() === '' ? NaN : Number(raw)
  return Number.isInteger(n) && n >= min && n <= max ? n : null
}

/** Positive finite number or null. */
export function positiveNumber(raw: string): number | null {
  const n = raw.trim() === '' ? NaN : Number(raw)
  return Number.isFinite(n) && n > 0 ? n : null
}
