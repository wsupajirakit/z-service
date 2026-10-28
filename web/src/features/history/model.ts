// Pure history logic.
import type { HistoryItem, HistoryRecord } from './schemas.ts'

/** Union of keys in first-seen order, so every column of every bar shows up once. */
export function recordColumns(records: HistoryRecord[]): string[] {
  const seen = new Set<string>()
  for (const r of records) for (const k of Object.keys(r)) seen.add(k)
  return [...seen]
}

export function filterHistory(items: readonly HistoryItem[], query: string): HistoryItem[] {
  const q = query.trim().toLowerCase()
  if (!q) return [...items]
  return items.filter((i) => i.symbol.toLowerCase().includes(q) || i.interval.toLowerCase() === q)
}
