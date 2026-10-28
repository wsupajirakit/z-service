import * as z from 'zod/mini'

// GET /api/history (backend/main.py get_history)
export const historyItemSchema = z.looseObject({
  id: z.number(),
  timestamp: z.string(),
  symbol: z.string(),
  exchange: z.nullish(z.string()),
  interval: z.string(),
  extended_session: z.boolean(),
})
export const historyListSchema = z.array(historyItemSchema)
export type HistoryItem = z.infer<typeof historyItemSchema>

// GET /api/history/{id}: the stored process_symbol() result, one record per bar
// (pandas to_dict('records'); columns depend on the formulas, so keep them open).
export const historyDetailSchema = z.array(z.record(z.string(), z.unknown()))
export type HistoryRecord = z.infer<typeof historyDetailSchema>[number]
