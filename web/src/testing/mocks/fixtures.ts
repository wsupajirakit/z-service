// Fake but realistic API payloads, shaped like the backend route functions return them.
// A handful of symbols only; never a copy of the real lists.
const T = (day: number, hour = 14) => `2026-10-${String(day).padStart(2, '0')}T${hour}:30:00+07:00`

export const versionFixture = {
  version: '0.9.0-mock', commit: 'abc1234def', build_time: '2026-10-24T09:00:00+00:00',
  symbols_count: 6, build_symbols: 5, missing_exchange: ['ZZZT'],
  job_phase: 'idle', job_round: 3, job_total: 6, autostart: false,
}

export const timezoneFixture = { offset_minutes: 420, label: 'Asia/Bangkok (UTC+7)' }

export const symbolsFixture = {
  count: 6,
  symbols: [
    { symbol: 'AAPL', name: 'Apple Inc.', exchange: 'NASDAQ' },
    { symbol: 'MSFT', name: 'Microsoft Corp.', exchange: 'NASDAQ' },
    { symbol: 'NVDA', name: 'NVIDIA Corp.', exchange: 'NASDAQ' },
    { symbol: 'KO', name: 'Coca-Cola Co.', exchange: 'NYSE' },
    { symbol: 'JPM', name: 'JPMorgan Chase', exchange: 'NYSE' },
    { symbol: 'SPY', name: 'SPDR S&P 500 ETF', exchange: 'AMEX' },
  ],
  missing_exchange: ['ZZZT'],
  sources: { build: 5, db_extra: 1 },
}

export const watchlistFixture = {
  Tech: [
    { symbol: 'AAPL', name: 'Apple Inc.', timestamp: T(20) },
    { symbol: 'MSFT', name: 'Microsoft Corp.', timestamp: T(21) },
    { symbol: 'NVDA', name: 'NVIDIA Corp.', timestamp: T(22) },
  ],
  Defensive: [
    { symbol: 'KO', name: 'Coca-Cola Co.', timestamp: T(18) },
    { symbol: 'JPM', name: 'JPMorgan Chase', timestamp: T(19) },
  ],
}

export const portfolioFixture = {
  Default: {
    positions: [
      { symbol: 'AAPL', total_quantity: 10, avg_price: 221.5 },
      { symbol: 'KO', total_quantity: 20, avg_price: 64.1 },
    ],
    history: [
      { symbol: 'AAPL', quantity: 12, buy_price: 220.0, timestamp: T(10), action: 'buy' },
      { symbol: 'AAPL', quantity: 2, buy_price: 230.0, timestamp: T(15), action: 'sell' },
      { symbol: 'KO', quantity: 20, buy_price: 64.1, timestamp: T(12), action: 'buy' },
    ],
  },
}

export const historyListFixture = [
  { id: 42, timestamp: T(23), symbol: 'NVDA', exchange: 'NASDAQ', interval: '1D',
    extended_session: false },
  { id: 41, timestamp: T(22), symbol: 'KO', exchange: 'NYSE', interval: '1W',
    extended_session: true },
]

export const historyDetailFixture = [
  { time: '2026-10-22', open: 181.2, high: 184.9, low: 180.1, close: 183.4, volume: 1.2e8,
    EMA_20: 178.3, RSI_14: 61.2 },
  { time: '2026-10-23', open: 183.5, high: 186.0, low: 182.7, close: 185.1, volume: 1.0e8,
    EMA_20: 179.0, RSI_14: 64.8 },
]

const roundMeta = (stamp: string, id: number, kill: number) => ({
  id, stamp, fingerprint: `fp${id}`, created_at: T(20 + id), asof_et: `2026-10-${20 + id} 16:00 ET`,
  data_age_hours: 2.5, timeframes: ['1W', '1D', '4H', '1H'], partial: false, list_name: null,
  screen_mode: 'full', universe: { all: 6, stocks: 5, etfs: 1, noneq: 0 },
  kill_pct: kill, kill_count: 2, kill_label: 'KILL 2/6', breadth_n: 6,
  regime_hint: 'risk-on', warnings: [],
})

export const roundListFixture = {
  rounds: [roundMeta('20261023-1600', 3, 33.3), roundMeta('20261022-1600', 2, 16.7)],
}

export const roundDetailFixture = (stamp: string) => ({
  ...roundMeta(stamp, 3, 33.3),
  digest_md: `# Digest ${stamp}\n\n- **AAPL** above EMA200\n- KO RSI 48\n\n`
    + '<b>raw html stays text</b>',
  full: { regime: { permission_hint: 'risk-on' } },
  packs: { short: [] },
})

export const roundStatusFixture = {
  status: 'done', phase: 'saving', message: 'saved', timeframes: ['1W', '1D'],
  list_name: null, stamp: '20261023-1600', reused: false,
  started_at: T(23, 15), finished_at: T(23, 16),
}

const tf = (count: number, at: string) => ({
  symbols_count: count, fetched_at_min: at, fetched_at_max: at, fetched_at_distinct: 1,
  duplicate_symbols: 0, rows_total: count, has_data: count > 0,
})

export const tfStatusFixture = {
  timeframes: { '1W': tf(6, T(23, 9)), '1D': tf(6, T(23, 10)), '4H': tf(5, T(23, 11)),
    '1H': tf(0, '') },
  list_name: null, newest_fetched_at: T(23, 11), generated_at: T(23, 12),
}

export const stockRadarFixture = [
  { id: 7, timestamp: T(21), symbols: ['AAPL', 'NVDA'], formulas: ['UIPT', 'Core Radar'],
    timeframes: ['1D', '4H'], extended_session: false,
    result_markdown: '## Result\n\n| Ticker | Score |\n|--|--|\n| NVDA | 8 |\n| AAPL | 6 |' },
]

export const earningScanFixture = [
  { id: 3, timestamp: T(19), symbols: ['MSFT', 'KO', 'ZZZT'], results: [
    { symbol: 'MSFT', provider: 'finnhub', next_earnings_date: '2026-10-28', history: [
      { period: '2026-06-30', eps_actual: 3.65, eps_estimate: 3.4, surprise_percent: 7.4,
        revenue_actual: 7.6e10, revenue_estimate: 7.4e10 }] },
    { symbol: 'KO', provider: 'alpha_vantage', next_earnings_date: null, history: [
      { period: '2026-06-30', eps_actual: '0.80', eps_estimate: '0.83', surprise_percent: '-3.6',
        revenue_actual: null, revenue_estimate: null }] },
    { symbol: 'ZZZT', provider: null, history: [], next_earnings_date: null,
      error: 'no provider had data' },
  ] },
]

export const jobIdleFixture = {
  mode: 'idle', status: 'idle', round: 0, timeframes: [], current_tf: null,
  current_symbol: null, current: 0, total: 0, step_index: 0, step_total: 0, phase: 'idle',
  cooldown_until: null, failed: [], started_at: null, finished_at: null,
  last_round_finished_at: null, message: '', logs: ['[mock] idle'],
}

export const tvTestFixture = {
  ok: true, verdict: 'Connected (mock)', verdict_level: 'ok', passed: 3, total: 3,
  duration: 1.2, logs: [
    { time: '09:00:01', level: 'info', message: 'auth mode: login' },
    { time: '09:00:02', level: 'ok', message: 'AAPL 1d: 5 bars' },
  ],
}

export const goldConfigFixture = {
  sources: [{ label: 'OANDA', exchange: 'OANDA' }, { label: 'IC Markets', exchange: 'ICMARKETS' }],
  timeframes: ['15m', '1h', '4h', '1d'],
  default_model: 'mock-model-fast',
}

export const goldModelsFixture = {
  models: [{ name: 'mock-model-fast', displayName: 'Mock fast' },
    { name: 'mock-model-pro', displayName: 'Mock pro' }],
  default: 'mock-model-fast',
}

export const goldModesFixture = {
  exchanges: ['ICMARKETS', 'OANDA'],
  modes: [{ mode: 'scalp', horizon: '1-4h' }, { mode: 'swing', horizon: '2-10d' }],
}

export const goldJobFixture = {
  status: 'idle', message: '', started_at: null, finished_at: null, folder_link: null,
  folder_name: null, result: null,
}

/** Deterministic bars for POST /api/data. */
export function barsFixture(symbol: string, rows: number) {
  const seed = [...symbol].reduce((s, c) => s + c.charCodeAt(0), 0)
  return Array.from({ length: rows }, (_, i) => {
    const open = 100 + (seed % 50) + Math.sin(i / 3) * 4
    const close = open + Math.cos(i / 2) * 2
    const day = new Date(Date.UTC(2026, 8, 1 + i)).toISOString().slice(0, 10)
    return { datetime: `${day} 00:00:00`, symbol, open, close,
      high: Math.max(open, close) + 1, low: Math.min(open, close) - 1, volume: 1e6 + i * 1e4 }
  })
}
