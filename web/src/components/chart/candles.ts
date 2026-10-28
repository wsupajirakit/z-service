// Pure: turn API bar records (`datetime` "YYYY-MM-DD HH:MM:SS", open/high/low/close) into
// chart candles. The wall-clock time is kept as-is (read as UTC) so the axis shows exchange time.
export type Candle = { time: number; open: number; high: number; low: number; close: number }

const STAMP = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?/

export function parseStamp(value: unknown): number | null {
  if (typeof value !== 'string') return null
  const g = STAMP.exec(value)
  if (!g) return null
  const [y, mo, d, h, mi, s] = g.slice(1).map((x) => Number(x ?? 0))
  return Date.UTC(y ?? 0, (mo ?? 1) - 1, d ?? 1, h ?? 0, mi ?? 0, s ?? 0) / 1000
}

const num = (v: unknown) => (typeof v === 'number' && Number.isFinite(v) ? v : null)

export function toCandles(rows: ReadonlyArray<Record<string, unknown>>): Candle[] {
  const byTime = new Map<number, Candle>()
  for (const r of rows) {
    const time = parseStamp(r.datetime ?? r.time)
    const [open, high, low, close] = [num(r.open), num(r.high), num(r.low), num(r.close)]
    if (time === null || open === null || high === null || low === null || close === null) continue
    byTime.set(time, { time, open, high, low, close })
  }
  return [...byTime.values()].sort((a, b) => a.time - b.time)
}
