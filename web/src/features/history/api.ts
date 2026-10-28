import { queryOptions, useQuery } from '@tanstack/react-query'
import { apiGet } from '../../services/api/client.ts'
import { appConfig } from '../../config/app.ts'
import { historyDetailSchema, historyListSchema } from './schemas.ts'

export const historyListQuery = queryOptions({
  queryKey: ['history'],
  queryFn: ({ signal }) => apiGet('history', historyListSchema, { signal }),
})

export const historyDetailQuery = (id: number) => queryOptions({
  queryKey: ['history', id],
  queryFn: ({ signal }) =>
    apiGet('history/{history_id}', historyDetailSchema, { path: { history_id: id }, signal }),
  // A stored result never changes.
  staleTime: appConfig.staleTime.static,
})

export const useHistoryList = () => useQuery(historyListQuery)
export const useHistoryDetail = (id: number) => useQuery(historyDetailQuery(id))
