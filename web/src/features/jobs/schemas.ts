import * as z from 'zod/mini'

// GET /api/automate/status: one shared state for the custom job and the auto loop.
export const jobSchema = z.looseObject({
  mode: z.string(),
  status: z.string(),
  round: z.optional(z.number()),
  timeframes: z.optional(z.array(z.string())),
  current_tf: z.nullish(z.string()),
  current_symbol: z.nullish(z.string()),
  current: z.optional(z.number()),
  total: z.optional(z.number()),
  phase: z.nullish(z.string()),
  cooldown_until: z.nullish(z.string()),
  failed: z.optional(z.array(z.string())),
  started_at: z.nullish(z.string()),
  finished_at: z.nullish(z.string()),
  message: z.nullish(z.string()),
  /** Set when the failure was an ApiError: translated like any API error. */
  message_code: z.nullish(z.string()),
  message_params: z.nullish(z.record(z.string(), z.union([z.string(), z.number()]))),
  logs: z.optional(z.array(z.string())),
})
export type Job = z.infer<typeof jobSchema>

// POST /api/automate, /api/auto/start, /api/auto/start_all, /api/auto/stop
export const startReplySchema = z.looseObject({
  status: z.string(),
  mode: z.optional(z.string()),
  symbols: z.optional(z.number()),
})
export type StartReply = z.infer<typeof startReplySchema>

// POST /api/tv/test
export const tvTestSchema = z.looseObject({
  ok: z.boolean(),
  verdict: z.string(),
  verdict_level: z.optional(z.string()),
  passed: z.optional(z.number()),
  total: z.optional(z.number()),
  duration: z.optional(z.number()),
  verdict_code: z.nullish(z.string()),
  logs: z.array(z.looseObject({
    time: z.string(),
    level: z.string(),
    message: z.string(),
    code: z.nullish(z.string()),
    params: z.nullish(z.record(z.string(), z.union([z.string(), z.number()]))),
  })),
})
export type TvTest = z.infer<typeof tvTestSchema>

// POST /api/data: bar records (pandas records; open-ended indicator columns).
export const barsSchema = z.array(z.record(z.string(), z.unknown()))
export type Bars = z.infer<typeof barsSchema>
