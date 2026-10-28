import { queryOptions, useQuery } from '@tanstack/react-query'
import { defineAction } from '../../services/api/action.ts'
import { apiGet, apiSend } from '../../services/api/client.ts'
import { appConfig } from '../../config/app.ts'
import { domainConfig } from '../../config/domain.ts'
import type { Target } from '../../utils/symbols.ts'
import { radarHistorySchema, scanResultSchema } from './schemas.ts'

export const radarHistoryQuery = queryOptions({
  queryKey: ['stock_radar', 'history'],
  queryFn: ({ signal }) => apiGet('stock_radar/history', radarHistorySchema, {
    query: { limit: appConfig.pageSize.stockRadarHistory },
    signal,
  }),
})

export const useRadarHistory = () => useQuery(radarHistoryQuery)

export type RadarScan = { targets: Target[]; formulas: string[]; timeframes: string[];
  extended: boolean; mode: string }

/** Paid: fetches every symbol x timeframe, then (mode "ai") asks the AI provider. */
export const scanAction = defineAction((v: RadarScan) =>
  apiSend('post', 'stock_radar/scan', scanResultSchema, {
    body: { symbols: v.targets, formulas: v.formulas, timeframes: v.timeframes,
      extended_session: v.extended, analysis_mode: v.mode,
      model: domainConfig.domain.stockRadarModel },
  }), [radarHistoryQuery.queryKey])
