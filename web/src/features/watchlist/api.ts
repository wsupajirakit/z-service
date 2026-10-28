import { apiSend } from '../../services/api/client.ts'
import { statusSchema } from '../../services/api/common.ts'
import { defineAction } from '../../services/api/action.ts'
import { symbolsQuery, watchlistQuery } from '../../services/api/lists.ts'

export { useWatchlist, watchlistQuery } from '../../services/api/lists.ts'

// The symbol list (/api/symbols) includes DB watchlist names, so it is refreshed too.
const touched = [watchlistQuery.queryKey, symbolsQuery.queryKey] as const

export type AddItem = { list: string; symbol: string; name: string; exchange: string | null }

export const addItemAction = defineAction((v: AddItem) =>
  apiSend('post', 'watchlist', statusSchema, {
    body: { list_name: v.list, symbol: v.symbol, name: v.name, exchange: v.exchange },
  }), touched)

export const removeItemAction = defineAction((v: { list: string; symbol: string }) =>
  apiSend('delete', 'watchlist/{list_name}/{symbol}', statusSchema, {
    path: { list_name: v.list, symbol: v.symbol },
  }), touched)

export const renameListAction = defineAction((v: { list: string; next: string }) =>
  apiSend('put', 'watchlist/{list_name}', statusSchema, {
    path: { list_name: v.list }, body: { new_name: v.next },
  }), touched)
