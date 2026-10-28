import { queryOptions, useQuery } from '@tanstack/react-query'
import { defineAction } from '../../services/api/action.ts'
import { apiGet, apiSend } from '../../services/api/client.ts'
import { statusSchema, type StatusReply } from '../../services/api/common.ts'
import { apiHref } from '../../services/api/url.ts'
import { appConfig } from '../../config/app.ts'
import { domainConfig } from '../../config/domain.ts'
import {
  goldAnalysisSchema, goldConfigSchema, goldJobSchema, goldModelsSchema, goldModesSchema,
  goldPriceSchema,
} from './schemas.ts'

const stale = appConfig.staleTime.static
export const goldConfigQuery = queryOptions({
  queryKey: ['gold', 'config'], staleTime: stale,
  queryFn: ({ signal }) => apiGet('gold/config', goldConfigSchema, { signal }),
})
export const goldModelsQuery = queryOptions({
  queryKey: ['gold', 'models'], staleTime: stale,
  queryFn: ({ signal }) => apiGet('gold/models', goldModelsSchema, { signal }),
})
export const goldModesQuery = queryOptions({
  queryKey: ['gold', 'modes'], staleTime: stale,
  queryFn: ({ signal }) => apiGet('gold/modes', goldModesSchema, { signal }),
})
/** Each read is a live TradingView fetch, so it runs only on demand (enabled: false). */
export const goldPriceQuery = (exchange: string) => queryOptions({
  queryKey: ['gold', 'price', exchange], enabled: false,
  queryFn: ({ signal }) => apiGet('gold/price', goldPriceSchema, { query: { exchange }, signal }),
})
export const goldJobQuery = queryOptions({
  queryKey: ['gold', 'status'],
  queryFn: ({ signal }) => apiGet('gold/status', goldJobSchema, { signal }),
  staleTime: appConfig.staleTime.status,
  refetchInterval: (q) => (q.state.data?.status === 'running' ? appConfig.poll.goldRunning : false),
})

export const useGoldConfig = () => useQuery(goldConfigQuery)
export const useGoldModels = () => useQuery(goldModelsQuery)
export const useGoldModes = () => useQuery(goldModesQuery)
export const useGoldPrice = (exchange: string) => useQuery(goldPriceQuery(exchange))
export const useGoldJob = () => useQuery(goldJobQuery)

export type GoldRun = { exchange: string; model: string }
const body = (v: GoldRun) => ({ exchange: v.exchange, model: v.model,
  rows: domainConfig.domain.goldRows })

export const analyzeAction = defineAction((v: GoldRun) =>
  apiSend('post', 'gold/analyze', goldAnalysisSchema, { body: body(v) }), [])
export const startGoldAction = defineAction((v: GoldRun) =>
  apiSend('post', 'gold/automate', statusSchema, { body: body(v) }), [goldJobQuery.queryKey])
export const stopGoldAction = defineAction<void, StatusReply>(() =>
  apiSend('post', 'gold/automate/stop', statusSchema), [goldJobQuery.queryKey])

export const goldExportHref = (mode: string, exchange: string) =>
  apiHref('gold/export', { mode, exchange })
