// Pure table logic shared by every list: text search, column sort, pagination.
export type CellValue = string | number | boolean | null | undefined
export type Sort = { id: string; desc: boolean } | null

/** Header click cycles ascending -> descending -> unsorted. */
export function nextSort(current: Sort, id: string): Sort {
  if (current?.id !== id) return { id, desc: false }
  return current.desc ? null : { id, desc: true }
}

const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' })

/** Numbers by value, text in natural order ("A2" before "A10"); empty values always last. */
export function compareValues(a: CellValue, b: CellValue): number {
  const emptyA = a === null || a === undefined || a === ''
  const emptyB = b === null || b === undefined || b === ''
  if (emptyA || emptyB) return Number(emptyA) - Number(emptyB)
  if (typeof a === 'number' && typeof b === 'number') return a - b
  return collator.compare(String(a), String(b))
}

/** Stable sort by one column; empty values stay last in both directions. */
export function sortRows<T>(rows: readonly T[], value: (row: T) => CellValue, desc: boolean): T[] {
  return rows
    .map((row, index) => ({ row, index, v: value(row) }))
    .sort((x, y) => {
      const empty = (v: CellValue) => v === null || v === undefined || v === ''
      if (empty(x.v) || empty(y.v)) return compareValues(x.v, y.v) || x.index - y.index
      const c = compareValues(x.v, y.v)
      return (desc ? -c : c) || x.index - y.index
    })
    .map((x) => x.row)
}

/** Case-insensitive "contains" over the given texts of each row. */
export function searchRows<T>(rows: readonly T[], query: string,
  texts: (row: T) => CellValue[]): T[] {
  const q = query.trim().toLowerCase()
  if (!q) return [...rows]
  return rows.filter((row) =>
    texts(row).some((v) => v !== null && v !== undefined && String(v).toLowerCase().includes(q)))
}

export type Page<T> = {
  rows: T[]
  /** 1-based index of the first and last row shown; 0 when there are none. */
  from: number
  to: number
  total: number
  pageIndex: number
  pageCount: number
}

/** One page of rows; an out-of-range page index snaps to the last page. */
export function paginate<T>(rows: readonly T[], pageIndex: number, pageSize: number): Page<T> {
  const total = rows.length
  const pageCount = Math.max(1, Math.ceil(total / pageSize))
  const index = Math.min(Math.max(0, pageIndex), pageCount - 1)
  const start = index * pageSize
  const slice = rows.slice(start, start + pageSize)
  return {
    rows: slice,
    from: total === 0 ? 0 : start + 1,
    to: start + slice.length,
    total,
    pageIndex: index,
    pageCount,
  }
}
