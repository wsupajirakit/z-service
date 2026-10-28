// Pure symbol-overview logic. Exchanges are derived from the data, never a fixed list.
import type { SymbolsInfo } from './schemas.ts'

export type ExchangeCount = { exchange: string; count: number }

export function exchangeCounts(info: SymbolsInfo): ExchangeCount[] {
  const counts = new Map<string, number>()
  for (const s of info.symbols) counts.set(s.exchange, (counts.get(s.exchange) ?? 0) + 1)
  return [...counts]
    .map(([exchange, count]) => ({ exchange, count }))
    .sort((a, b) => b.count - a.count || a.exchange.localeCompare(b.exchange))
}
