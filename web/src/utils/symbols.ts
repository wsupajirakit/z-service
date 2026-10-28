// Pure helpers for symbol pickers: filter, list → symbols, attach exchanges.
import type { SymbolInfo, Watchlists } from '../services/api/lists.ts'

export type Target = { symbol: string; exchange: string }

export function filterSymbols(all: SymbolInfo[], query: string, limit: number): SymbolInfo[] {
  const q = query.trim().toLowerCase()
  const hits = q
    ? all.filter((s) => s.symbol.toLowerCase().includes(q)
      || (s.name ?? '').toLowerCase().includes(q))
    : all
  return hits.slice(0, limit)
}

export function listSymbols(lists: Watchlists, list: string): string[] {
  return [...new Set((lists[list] ?? []).map((i) => i.symbol))].sort()
}

/** Symbols with a known exchange (the fetch jobs need both); unknown ones are reported. */
export function toTargets(symbols: string[], all: SymbolInfo[]):
  { targets: Target[]; missing: string[] } {
  const bySymbol = new Map(all.map((s) => [s.symbol, s.exchange]))
  const targets: Target[] = []
  const missing: string[] = []
  for (const symbol of symbols) {
    const exchange = bySymbol.get(symbol)
    if (exchange) targets.push({ symbol, exchange })
    else missing.push(symbol)
  }
  return { targets, missing }
}

export function toggle(list: string[], item: string, on: boolean): string[] {
  return on ? [...new Set([...list, item])] : list.filter((x) => x !== item)
}
