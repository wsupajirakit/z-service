// Pure watchlist logic: flatten lists into rows, filter, count.
import { cleanExchange, cleanName, cleanSymbol } from '../../utils/validate.ts'
import type { Watchlists } from './schemas.ts'

export type WatchRow = { list: string; symbol: string; name: string; timestamp: string | null }
export type ListCount = { list: string; count: number }

export function toRows(lists: Watchlists): WatchRow[] {
  return Object.entries(lists).flatMap(([list, items]) =>
    items.map((it) => ({
      list,
      symbol: it.symbol,
      name: it.name ?? '',
      timestamp: it.timestamp ?? null,
    })),
  )
}

export function listCounts(lists: Watchlists): ListCount[] {
  return Object.entries(lists)
    .map(([list, items]) => ({ list, count: items.length }))
    .sort((a, b) => a.list.localeCompare(b.list))
}

/** Case-insensitive match on symbol or name; `list` null means every list. */
export function filterRows(rows: readonly WatchRow[], query: string,
  list: string | null): WatchRow[] {
  const q = query.trim().toLowerCase()
  return rows.filter((r) => {
    if (list !== null && r.list !== list) return false
    if (!q) return true
    return r.symbol.toLowerCase().includes(q) || r.name.toLowerCase().includes(q)
  })
}

export type FieldResult<T> = { ok: true; value: T } | { ok: false; field: string }

/** Validates the add-symbol form; the name defaults to the symbol, exchange is optional. */
export function parseAddItem(form: { list: string; symbol: string; name: string;
  exchange: string }): FieldResult<{ list: string; symbol: string; name: string;
  exchange: string | null }> {
  const list = cleanName(form.list)
  if (!list) return { ok: false, field: 'list' }
  const symbol = cleanSymbol(form.symbol)
  if (!symbol) return { ok: false, field: 'symbol' }
  const exchange = form.exchange.trim() === '' ? null : cleanExchange(form.exchange)
  if (exchange === null && form.exchange.trim() !== '') return { ok: false, field: 'exchange' }
  return { ok: true, value: { list, symbol, name: form.name.trim() || symbol, exchange } }
}
