import * as z from 'zod/mini'

// Shapes from backend/radar_api.py + radar_engine/adapter.py (no response models there).
const nstr = z.nullish(z.string())
const nnum = z.nullish(z.number())
const params = z.nullish(z.record(z.string(), z.union([z.string(), z.number()])))
/** A coded server text (zservice/core/messages.py). */
const codedText = z.looseObject({ code: z.string(), params, text: z.string() })

export const roundMetaSchema = z.looseObject({
  id: nnum,
  stamp: z.string(),
  created_at: nstr,
  asof_et: nstr,
  data_age_hours: nnum,
  timeframes: z.optional(z.array(z.string())),
  partial: z.optional(z.boolean()),
  list_name: nstr,
  screen_mode: nstr,
  universe: z.optional(z.looseObject({
    all: z.optional(z.number()),
    stocks: z.optional(z.number()),
    etfs: z.optional(z.number()),
    noneq: z.optional(z.number()),
  })),
  kill_pct: nnum,
  kill_count: nnum,
  kill_label: nstr,
  breadth_n: nnum,
  regime_hint: nstr,
  warnings: z.optional(z.array(z.unknown())),
  /** Rounds stored since 25 Oct also carry the warnings as codes (translated by the UI). */
  warnings_coded: z.optional(z.array(codedText)),
})
export type RoundMeta = z.infer<typeof roundMetaSchema>

export const roundListSchema = z.looseObject({ rounds: z.array(roundMetaSchema) })

// GET /api/radar_round/{stamp}: meta + digest_md + parsed full/packs (opaque here).
export const roundDetailSchema = z.extend(roundMetaSchema, {
  digest_md: nstr,
  full: z.optional(z.unknown()),
  packs: z.optional(z.unknown()),
})
export type RoundDetail = z.infer<typeof roundDetailSchema>

export const roundStatusSchema = z.looseObject({
  status: z.string(),
  phase: nstr,
  message: nstr,
  message_code: nstr,
  message_params: params,
  timeframes: z.optional(z.array(z.string())),
  list_name: nstr,
  stamp: nstr,
  started_at: nstr,
  finished_at: nstr,
  error: nstr,
})
export type RoundStatus = z.infer<typeof roundStatusSchema>

export const tfEntrySchema = z.looseObject({
  symbols_count: z.number(),
  fetched_at_min: nstr,
  fetched_at_max: nstr,
  fetched_at_distinct: z.optional(z.number()),
  duplicate_symbols: z.optional(z.number()),
  rows_total: z.optional(z.number()),
  has_data: z.boolean(),
})
export type TfEntry = z.infer<typeof tfEntrySchema>

export const tfStatusSchema = z.looseObject({
  timeframes: z.record(z.string(), tfEntrySchema),
  list_name: nstr,
  newest_fetched_at: nstr,
  generated_at: nstr,
})
export type TfStatus = z.infer<typeof tfStatusSchema>
