// Test helper: server-renders a page with a query cache pre-filled from the fixtures,
// so render tests need no DOM library and no network.
import type { ReactNode } from 'react'
import { renderToString } from 'react-dom/server'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { timezoneQuery, versionQuery } from '../../services/api/common.ts'
import { timezoneFixture, versionFixture } from './fixtures.ts'

export function renderPage(node: ReactNode, seed: Array<[readonly unknown[], unknown]>): string {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  client.setQueryData(versionQuery.queryKey, versionFixture)
  client.setQueryData(timezoneQuery.queryKey, timezoneFixture)
  for (const [key, data] of seed) client.setQueryData(key, data)
  return renderToString(<QueryClientProvider client={client}>{node}</QueryClientProvider>)
}
