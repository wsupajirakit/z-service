import { queryOptions, useQuery } from '@tanstack/react-query'
import { defineAction } from '../../services/api/action.ts'
import { apiGet, apiSend } from '../../services/api/client.ts'
import { appConfig } from '../../config/app.ts'
import { earningHistorySchema, earningScanResultSchema } from './schemas.ts'

export const earningHistoryQuery = queryOptions({
  queryKey: ['earning_scan', 'history'],
  queryFn: ({ signal }) => apiGet('earning_scan/history', earningHistorySchema, {
    query: { limit: appConfig.pageSize.earningScanHistory },
    signal,
  }),
})

export const useEarningHistory = () => useQuery(earningHistoryQuery)

/** Paid: one or more data-provider calls per symbol (Finnhub, FMP, Alpha Vantage). */
export const earningScanAction = defineAction((symbols: string[]) =>
  apiSend('post', 'earning_scan/scan', earningScanResultSchema, { body: { symbols } }),
[earningHistoryQuery.queryKey])
