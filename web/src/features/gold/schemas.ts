import * as z from 'zod/mini'

export const goldConfigSchema = z.looseObject({
  sources: z.array(z.looseObject({ label: z.string(), exchange: z.string() })),
  timeframes: z.array(z.string()),
  default_model: z.string(),
})
export const goldPriceSchema = z.looseObject({ price: z.nullish(z.number()) })
export const goldModelsSchema = z.looseObject({
  models: z.array(z.looseObject({ name: z.string(), displayName: z.nullish(z.string()) })),
  default: z.string(),
})
export const goldModesSchema = z.looseObject({
  exchanges: z.array(z.string()),
  modes: z.array(z.looseObject({ mode: z.string(), horizon: z.nullish(z.string()) })),
})
export const goldAnalysisSchema = z.looseObject({
  exchange: z.string(),
  model: z.string(),
  latest_price: z.nullish(z.number()),
  analysis: z.string(),
  generated_at: z.nullish(z.string()),
})
export type GoldAnalysis = z.infer<typeof goldAnalysisSchema>
export const goldJobSchema = z.looseObject({
  status: z.string(),
  message: z.nullish(z.string()),
  message_code: z.nullish(z.string()),
  message_params: z.nullish(z.record(z.string(), z.union([z.string(), z.number()]))),
  started_at: z.nullish(z.string()),
  finished_at: z.nullish(z.string()),
  folder_link: z.nullish(z.string()),
  folder_name: z.nullish(z.string()),
})
export type GoldJob = z.infer<typeof goldJobSchema>
