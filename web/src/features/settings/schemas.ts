import * as z from 'zod/mini'

export { timezoneSchema, type TimezoneSetting } from '../../services/api/common.ts'

// GET/POST /api/settings/destinations: all four flags, unset means on.
export const destinationsSchema = z.looseObject({
  dest_stock_drive: z.boolean(),
  dest_stock_telegram: z.boolean(),
  dest_gold_drive: z.boolean(),
  dest_gold_telegram: z.boolean(),
})
export type Destinations = z.infer<typeof destinationsSchema>
export type DestinationKey =
  | 'dest_stock_drive' | 'dest_stock_telegram' | 'dest_gold_drive' | 'dest_gold_telegram'
export const destinationKeys: DestinationKey[] = [
  'dest_stock_drive', 'dest_stock_telegram', 'dest_gold_drive', 'dest_gold_telegram',
]

export const minutesSchema = z.looseObject({ minutes: z.number() })
export const tvModeSchema = z.looseObject({ mode: z.number() })

// GET/POST /api/settings/tv_token: expiry info only, never the token itself.
export const tvTokenSchema = z.looseObject({
  status: z.string(),
  expires_in_minutes: z.optional(z.number()),
})
export type TvTokenStatus = z.infer<typeof tvTokenSchema>

// POST /api/auth/password: every older session is revoked; this is the caller's new token.
export const passwordChangedSchema = z.looseObject({ status: z.string(), token: z.string() })
