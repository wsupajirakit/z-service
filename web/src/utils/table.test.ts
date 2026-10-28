import { describe, expect, it } from 'vitest'
import { compareValues, nextSort, paginate, searchRows, sortRows } from './table.ts'

type Row = { sym: string; n: number | null }
const rows: Row[] = [
  { sym: 'MSFT', n: 3 }, { sym: 'A10', n: null }, { sym: 'aapl', n: 1 }, { sym: 'A2', n: 2 },
]

describe('table logic', () => {
  it('header clicks cycle ascending, descending, unsorted', () => {
    const asc = nextSort(null, 'sym')
    expect(asc).toEqual({ id: 'sym', desc: false })
    expect(nextSort(asc, 'sym')).toEqual({ id: 'sym', desc: true })
    expect(nextSort({ id: 'sym', desc: true }, 'sym')).toBeNull()
    expect(nextSort({ id: 'sym', desc: true }, 'n')).toEqual({ id: 'n', desc: false })
  })

  it('compares numbers by value and text in natural, case-blind order', () => {
    expect(compareValues(2, 10)).toBeLessThan(0)
    expect(compareValues('A2', 'A10')).toBeLessThan(0)
    expect(compareValues('aapl', 'AAPL')).toBe(0)
    expect(compareValues(null, 1)).toBeGreaterThan(0)
  })

  it('sorts both ways with empty values last', () => {
    expect(sortRows(rows, (r) => r.n, false).map((r) => r.n)).toEqual([1, 2, 3, null])
    expect(sortRows(rows, (r) => r.n, true).map((r) => r.n)).toEqual([3, 2, 1, null])
    expect(sortRows(rows, (r) => r.sym, false).map((r) => r.sym))
      .toEqual(['A2', 'A10', 'aapl', 'MSFT'])
  })

  it('searches the given texts, case-insensitive, and keeps every row for an empty query', () => {
    expect(searchRows(rows, ' ms ', (r) => [r.sym]).map((r) => r.sym)).toEqual(['MSFT'])
    expect(searchRows(rows, 'a', (r) => [r.sym])).toHaveLength(3)
    expect(searchRows(rows, '', (r) => [r.sym])).toHaveLength(4)
    expect(searchRows(rows, '3', (r) => [r.sym, r.n]).map((r) => r.sym)).toEqual(['MSFT'])
  })

  it('pages with 1-based ranges and snaps an out-of-range page to the last one', () => {
    const many = Array.from({ length: 23 }, (_, i) => i)
    expect(paginate(many, 0, 10)).toMatchObject({ from: 1, to: 10, total: 23, pageCount: 3 })
    const last = paginate(many, 2, 10)
    expect(last).toMatchObject({ from: 21, to: 23, pageIndex: 2 })
    expect(last.rows).toEqual([20, 21, 22])
    expect(paginate(many, 9, 10).pageIndex).toBe(2)
    expect(paginate([], 0, 10)).toMatchObject({ from: 0, to: 0, total: 0, pageCount: 1 })
  })
})
