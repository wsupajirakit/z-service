// Symbol and watchlist reads used by several features (pickers on jobs, export, scans).
// Features must not import each other, so the queries and their schemas live here.
import { queryOptions, useQuery } from '@tanstack/react-query'
import * as z from 'zod/mini'
import { appConfig } from '../../config/app.ts'
import { apiGet } from './client.ts'

// GET /api/symbols: build-time list ∪ DB watchlist names.
export const symbolSchema = z.looseObject({
  symbol: z.string(),
  name: z.nullish(z.string()),
  exchange: z.string(),
})
export const symbolsSchema = z.looseObject({
  count: z.number(),
  symbols: z.array(symbolSchema),
  missing_exchange: z.array(z.string()),
  sources: z.optional(z.looseObject({ build: z.number(), db_extra: z.number() })),
})
export type SymbolInfo = z.infer<typeof symbolSchema>
export type SymbolsInfo = z.infer<typeof symbolsSchema>

// GET /api/watchlist -> { [list_name]: [{ symbol, name, timestamp, exchange? }] }
export const watchItemSchema = z.looseObject({
  symbol: z.string(),
  name: z.nullish(z.string()),
  exchange: z.nullish(z.string()),
  timestamp: z.nullish(z.string()),
})
export const watchlistSchema = z.record(z.string(), z.array(watchItemSchema))
export type Watchlists = z.infer<typeof watchlistSchema>

export const symbolsQuery = queryOptions({
  queryKey: ['symbols'],
  queryFn: ({ signal }) => apiGet('symbols', symbolsSchema, { signal }),
  staleTime: appConfig.staleTime.static,
})

export const watchlistQuery = queryOptions({
  queryKey: ['watchlist'],
  queryFn: ({ signal }) => apiGet('watchlist', watchlistSchema, { signal }),
})

export const useSymbols = () => useQuery(symbolsQuery)
export const useWatchlist = () => useQuery(watchlistQuery)
