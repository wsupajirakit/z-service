import { QueryClient } from '@tanstack/react-query'
import { shouldRetry } from '../services/api/error.ts'
import { appConfig } from '../config/app.ts'

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: appConfig.staleTime.list,
        refetchOnWindowFocus: true,
        // Polling pauses while the tab is hidden.
        refetchIntervalInBackground: false,
        retry: shouldRetry,
      },
    },
  })
}

export const queryClient = createQueryClient()
