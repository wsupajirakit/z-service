import { queryOptions, useQuery } from '@tanstack/react-query'
import { defineAction } from '../../services/api/action.ts'
import { apiGet, apiSend } from '../../services/api/client.ts'
import { appConfig } from '../../config/app.ts'
import type { Target } from '../../utils/symbols.ts'
import { barsSchema, jobSchema, startReplySchema, tvTestSchema } from './schemas.ts'
import type { StartReply, TvTest } from './schemas.ts'
import { jobPollMs } from './model.ts'

export const jobQuery = queryOptions({
  queryKey: ['automate', 'status'],
  queryFn: ({ signal }) => apiGet('automate/status', jobSchema, { signal }),
  staleTime: appConfig.staleTime.status,
  // Faster while running; paused while the tab is hidden (queryClient default).
  refetchInterval: (q) => jobPollMs(q.state.data),
})
export const useJob = () => useQuery(jobQuery)

const touched = [jobQuery.queryKey, ['version']] as const

export type AutoStart = { targets: Target[]; rows: number; forceAllTf: boolean }

export const startAutoAction = defineAction((v: AutoStart) =>
  apiSend('post', 'auto/start', startReplySchema, {
    body: { symbols: v.targets, rows: v.rows, force_all_tf: v.forceAllTf },
  }), touched)

/** Server picks the symbol list (build ∪ DB), rows 80, default CSV mode. */
export const startAllAction = defineAction<void, StartReply>(() =>
  apiSend('post', 'auto/start_all', startReplySchema), touched)

export const stopAction = defineAction<void, StartReply>(() =>
  apiSend('post', 'auto/stop', startReplySchema), touched)

export type CustomRun = { timeframes: string[]; targets: Target[]; rows: number;
  extended: boolean }

export const customRunAction = defineAction((v: CustomRun) =>
  apiSend('post', 'automate', startReplySchema, {
    body: { timeframes: v.timeframes, symbols: v.targets, rows: v.rows,
      extended_session: v.extended },
  }), touched)

export const tvTestAction = defineAction<void, TvTest>(() =>
  apiSend('post', 'tv/test', tvTestSchema), [])

export type DataFetch = { symbol: string; exchange: string; interval: string; rows: number;
  extended: boolean }

/** One symbol, one timeframe; the backend also stores it in history. */
export const fetchDataAction = defineAction((v: DataFetch) =>
  apiSend('post', 'data', barsSchema, {
    body: { symbol: v.symbol, exchange: v.exchange, interval: v.interval, rows: v.rows,
      extended_session: v.extended },
  }), [['history']])
