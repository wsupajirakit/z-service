import { queryOptions, useQuery } from '@tanstack/react-query'
import * as z from 'zod/mini'
import { defineAction } from '../../services/api/action.ts'
import { apiGet, apiSend } from '../../services/api/client.ts'
import { appConfig } from '../../config/app.ts'
import { isRunning } from './model.ts'
import { roundDetailSchema, roundListSchema, roundStatusSchema, tfStatusSchema } from './schemas.ts'

export const roundListQuery = queryOptions({
  queryKey: ['radar_round', 'list'],
  queryFn: ({ signal }) => apiGet('radar_round/list', roundListSchema, {
    query: { limit: appConfig.pageSize.radarRounds },
    signal,
  }),
})

export const roundStatusQuery = queryOptions({
  queryKey: ['radar_round', 'status'],
  queryFn: ({ signal }) => apiGet('radar_round/status', roundStatusSchema, { signal }),
  staleTime: appConfig.staleTime.status,
  // Poll only while a round runs; TanStack Query pauses it when the tab is hidden.
  refetchInterval: (q) => (isRunning(q.state.data) ? appConfig.poll.radarStatus : false),
})

export const tfStatusQuery = queryOptions({
  queryKey: ['radar_round', 'tf_status'],
  queryFn: ({ signal }) => apiGet('radar_round/tf_status', tfStatusSchema, { signal }),
  staleTime: appConfig.staleTime.status,
})

export const roundDetailQuery = (stamp: string) => queryOptions({
  queryKey: ['radar_round', 'detail', stamp],
  queryFn: ({ signal }) =>
    apiGet('radar_round/{stamp}', roundDetailSchema, { path: { stamp }, signal }),
  staleTime: appConfig.staleTime.static,
})

export const useRoundList = () => useQuery(roundListQuery)
export const useRoundStatus = () => useQuery(roundStatusQuery)
export const useTfStatus = () => useQuery(tfStatusQuery)
export const useRoundDetail = (stamp: string) => useQuery(roundDetailQuery(stamp))

export type RoundRun = { timeframes: string[]; newRecord: boolean }

/** Answers with the same shape as /status, so the status query is seeded and polls on. */
export const runRoundAction = defineAction((v: RoundRun) =>
  apiSend('post', 'radar_round/run', roundStatusSchema, {
    body: { timeframes: v.timeframes, new_record: v.newRecord },
  }), [roundStatusQuery.queryKey, roundListQuery.queryKey])

export const deleteRoundAction = defineAction((stamp: string) =>
  apiSend('delete', 'radar_round/{stamp}', z.looseObject({ status: z.string() }), {
    path: { stamp },
  }), [roundListQuery.queryKey])
