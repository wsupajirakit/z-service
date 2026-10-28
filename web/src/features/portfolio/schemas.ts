import * as z from 'zod/mini'

// GET /api/portfolio -> { [port_name]: { positions: [...], history: [...] } } (backend/main.py)
export const positionSchema = z.looseObject({
  symbol: z.string(),
  total_quantity: z.number(),
  avg_price: z.number(),
})
export const tradeSchema = z.looseObject({
  symbol: z.string(),
  quantity: z.number(),
  buy_price: z.number(),
  timestamp: z.nullish(z.string()),
  action: z.string(),
})
export const portfolioSchema = z.record(z.string(), z.looseObject({
  positions: z.array(positionSchema),
  history: z.array(tradeSchema),
}))
export type Portfolios = z.infer<typeof portfolioSchema>
export type Position = z.infer<typeof positionSchema>
export type Trade = z.infer<typeof tradeSchema>
