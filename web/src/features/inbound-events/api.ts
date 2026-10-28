import { queryOptions, useQuery } from '@tanstack/react-query'
import { apiGet } from '../../services/api/client.ts'
import { inboundEventsSchema } from './schemas.ts'

export const inboundEventsQuery = queryOptions({
  queryKey: ['inbound-events'],
  queryFn: ({ signal }) => apiGet('inbound-events', inboundEventsSchema, { signal }),
  refetchInterval: 10_000,
})

export const useInboundEvents = () => useQuery(inboundEventsQuery)
