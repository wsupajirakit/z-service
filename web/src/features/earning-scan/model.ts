// Pure earning-scan logic.
import type { Quarter, SymbolResult } from './schemas.ts'

export function toNumber(value: unknown): number | null {
  const n = typeof value === 'string' && value.trim() !== '' ? Number(value) : value
  return typeof n === 'number' && Number.isFinite(n) ? n : null
}

/** Latest reported quarter: the first entry with an actual EPS (providers list newest first). */
export function latestQuarter(result: SymbolResult): Quarter | null {
  return (result.history ?? []).find((q) => toNumber(q.eps_actual) !== null) ?? null
}

/** Beat (+1), miss (-1) or unknown (0) for EPS actual vs estimate. */
export function epsVerdict(q: Quarter | null): -1 | 0 | 1 {
  const actual = toNumber(q?.eps_actual)
  const estimate = toNumber(q?.eps_estimate)
  if (actual === null || estimate === null) return 0
  if (actual > estimate) return 1
  return actual < estimate ? -1 : 0
}
