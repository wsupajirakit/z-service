import { describe, expect, it } from 'vitest'
import { parseStamp, toCandles } from './candles.ts'

describe('toCandles', () => {
  it('parses stamps, drops bad rows, sorts ascending and dedupes', () => {
    expect(parseStamp('2026-10-23 09:30:00')).toBe(Date.UTC(2026, 9, 23, 9, 30) / 1000)
    expect(parseStamp('nope')).toBeNull()
    const c = toCandles([
      { datetime: '2026-10-23 00:00:00', open: 2, high: 3, low: 1, close: 2.5 },
      { datetime: '2026-10-22 00:00:00', open: 1, high: 2, low: 0.5, close: 2 },
      { datetime: '2026-10-22 00:00:00', open: 1, high: 2, low: 0.5, close: 2.1 },
      { datetime: '2026-10-24 00:00:00', open: null, high: 3, low: 1, close: 2 },
    ])
    expect(c.map((x) => x.close)).toEqual([2.1, 2.5])
  })
})
