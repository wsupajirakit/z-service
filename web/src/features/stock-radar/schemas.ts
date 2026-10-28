import * as z from 'zod/mini'

// GET /api/stock_radar/history (backend/main.py stock_radar_history)
export const radarRunSchema = z.looseObject({
  id: z.number(),
  timestamp: z.string(),
  symbols: z.array(z.string()),
  formulas: z.array(z.unknown()),
  timeframes: z.array(z.string()),
  extended_session: z.boolean(),
  result_markdown: z.nullish(z.string()),
})
export const radarHistorySchema = z.array(radarRunSchema)
export type RadarRun = z.infer<typeof radarRunSchema>

// POST /api/stock_radar/scan
export const scanResultSchema = z.looseObject({
  analysis: z.string(),
  timestamp: z.nullish(z.string()),
})
