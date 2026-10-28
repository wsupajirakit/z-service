import * as z from 'zod/mini'

// GET /api/earning_scan/history (backend/main.py). Provider values can be numbers or
// numeric strings (Alpha Vantage), so quarter fields accept both.
const numish = z.nullish(z.union([z.number(), z.string()]))

export const quarterSchema = z.looseObject({
  period: z.nullish(z.string()),
  eps_actual: numish,
  eps_estimate: numish,
  surprise_percent: numish,
  revenue_actual: numish,
  revenue_estimate: numish,
})
export type Quarter = z.infer<typeof quarterSchema>

export const symbolResultSchema = z.looseObject({
  symbol: z.string(),
  provider: z.nullish(z.string()),
  history: z.optional(z.array(quarterSchema)),
  next_earnings_date: z.nullish(z.string()),
  error: z.nullish(z.string()),
  error_code: z.nullish(z.string()),
})
export type SymbolResult = z.infer<typeof symbolResultSchema>

export const earningRunSchema = z.looseObject({
  id: z.number(),
  timestamp: z.string(),
  symbols: z.array(z.string()),
  results: z.array(symbolResultSchema),
})
export const earningHistorySchema = z.array(earningRunSchema)
export type EarningRun = z.infer<typeof earningRunSchema>

// POST /api/earning_scan/scan
export const earningScanResultSchema = z.looseObject({
  results: z.array(symbolResultSchema),
  timestamp: z.nullish(z.string()),
})
