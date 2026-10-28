// In-memory state behind the MSW handlers, so writes in `dev:mock` are visible on the next
// read. Tests call resetDb() after each case; nothing here talks to a real backend.
import * as f from './fixtures.ts'

type Item = { symbol: string; name: string; exchange?: string | null; timestamp: string }
type TradeRow = { symbol: string; quantity: number; buy_price: number; timestamp: string;
  action: string }

const clone = <T>(v: T): T => structuredClone(v)

export const MOCK_USER = 'me'
export const MOCK_PASSWORD = 'current-password-ok'

function initial() {
  return {
    watchlist: clone(f.watchlistFixture) as Record<string, Item[]>,
    trades: Object.fromEntries(Object.entries(f.portfolioFixture)
      .map(([k, v]) => [k, clone(v.history)])) as Record<string, TradeRow[]>,
    timezone: clone(f.timezoneFixture),
    destinations: { dest_stock_drive: true, dest_stock_telegram: true, dest_gold_drive: false,
      dest_gold_telegram: true },
    autoSkip: 15,
    tvMode: 1,
    tvToken: { status: 'none' } as { status: string; expires_in_minutes?: number },
    password: MOCK_PASSWORD,
    registered: true,
    job: clone(f.jobIdleFixture) as Record<string, unknown>,
    gold: clone(f.goldJobFixture) as Record<string, unknown>,
    history: clone(f.historyListFixture),
    rounds: clone(f.roundListFixture.rounds),
    roundStatus: clone(f.roundStatusFixture) as Record<string, unknown>,
    stockRadar: clone(f.stockRadarFixture),
    earning: clone(f.earningScanFixture) as Array<Record<string, unknown>>,
  }
}

export let db = initial()

export function resetDb(): void {
  db = initial()
}

/** Backend summarize(): net quantity per symbol, average price of the buys. */
export function portfolioView() {
  return Object.fromEntries(Object.entries(db.trades).map(([port, rows]) => {
    const acc = new Map<string, { qty: number; buyQty: number; buyCost: number }>()
    for (const r of rows) {
      const a = acc.get(r.symbol) ?? { qty: 0, buyQty: 0, buyCost: 0 }
      a.qty += r.action === 'sell' ? -r.quantity : r.quantity
      if (r.action === 'buy') {
        a.buyQty += r.quantity
        a.buyCost += r.quantity * r.buy_price
      }
      acc.set(r.symbol, a)
    }
    const positions = [...acc].filter(([, a]) => a.qty > 0).map(([symbol, a]) => ({
      symbol, total_quantity: a.qty, avg_price: a.buyQty ? a.buyCost / a.buyQty : 0,
    }))
    return [port, { positions, history: rows }]
  }))
}

export const nowIso = () => new Date().toISOString()
