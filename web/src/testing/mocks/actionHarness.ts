// Test helper: run a write action against the MSW handlers with a fresh QueryClient and
// report which seeded queries it invalidated.
import { QueryClient, type QueryKey } from '@tanstack/react-query'
import { runAction, type Action } from '../../services/api/action.ts'

export async function runWithCache<V, D>(action: Action<V, D>, vars: V, seeded: QueryKey[]) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  for (const key of seeded) client.setQueryData(key, {})
  const data = await runAction(client, action, vars)
  const invalidated = seeded.filter((k) => client.getQueryState(k)?.isInvalidated)
  return { data, invalidated }
}
