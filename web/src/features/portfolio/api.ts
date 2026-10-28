import { queryOptions, useQuery } from '@tanstack/react-query'
import { defineAction } from '../../services/api/action.ts'
import { apiGet, apiSend } from '../../services/api/client.ts'
import { statusSchema } from '../../services/api/common.ts'
import { portfolioSchema } from './schemas.ts'

export const portfolioQuery = queryOptions({
  queryKey: ['portfolio'],
  queryFn: ({ signal }) => apiGet('portfolio', portfolioSchema, { signal }),
})

export const usePortfolio = () => useQuery(portfolioQuery)

const touched = [portfolioQuery.queryKey] as const

export type TradeInput = {
  port: string
  symbol: string
  quantity: number
  price: number
  action: 'buy' | 'sell'
}

export const addTradeAction = defineAction((v: TradeInput) =>
  apiSend('post', 'portfolio', statusSchema, {
    body: { port_name: v.port, symbol: v.symbol, quantity: v.quantity, buy_price: v.price,
      action: v.action },
  }), touched)

export const removeSymbolAction = defineAction((v: { port: string; symbol: string }) =>
  apiSend('delete', 'portfolio/{port_name}/{symbol}', statusSchema, {
    path: { port_name: v.port, symbol: v.symbol },
  }), touched)

export const renamePortAction = defineAction((v: { port: string; next: string }) =>
  apiSend('put', 'portfolio/{port_name}', statusSchema, {
    path: { port_name: v.port }, body: { new_name: v.next },
  }), touched)
