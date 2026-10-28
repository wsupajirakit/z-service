// Pure portfolio logic. Positions arrive already netted by the backend (avg cost of buys).
import { cleanName, cleanSymbol, intInRange, positiveNumber } from '../../utils/validate.ts'
import type { Portfolios, Position, Trade } from './schemas.ts'

export type PortSummary = { name: string; positions: Position[]; trades: Trade[]; cost: number }

export function costBasis(positions: Position[]): number {
  return positions.reduce((sum, p) => sum + p.total_quantity * p.avg_price, 0)
}

/** Ports sorted by name; trades newest first (ISO timestamps sort as text). */
export function summarize(ports: Portfolios): PortSummary[] {
  return Object.entries(ports)
    .map(([name, p]) => ({
      name,
      positions: [...p.positions].sort((a, b) => a.symbol.localeCompare(b.symbol)),
      trades: [...p.history].sort((a, b) => (b.timestamp ?? '').localeCompare(a.timestamp ?? '')),
      cost: costBasis(p.positions),
    }))
    .sort((a, b) => a.name.localeCompare(b.name))
}

export type TradeForm = { port: string; symbol: string; quantity: string; price: string;
  action: 'buy' | 'sell' }
type TradeParsed = { port: string; symbol: string; quantity: number; price: number;
  action: 'buy' | 'sell' }

/** Validates the add-trade form: whole-share quantity (backend int), positive price. */
export function parseTrade(f: TradeForm):
  { ok: true; value: TradeParsed } | { ok: false; field: keyof TradeForm } {
  const port = cleanName(f.port)
  if (!port) return { ok: false, field: 'port' }
  const symbol = cleanSymbol(f.symbol)
  if (!symbol) return { ok: false, field: 'symbol' }
  const quantity = intInRange(f.quantity, 1, 1_000_000_000)
  if (quantity === null) return { ok: false, field: 'quantity' }
  const price = positiveNumber(f.price)
  if (price === null) return { ok: false, field: 'price' }
  return { ok: true, value: { port, symbol, quantity, price, action: f.action } }
}
