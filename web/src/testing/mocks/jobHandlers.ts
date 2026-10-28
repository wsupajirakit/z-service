// Jobs, TradingView test, single fetch, exports, gold and the paid scans. Every "paid" call
// here is fake: no AI or data provider is ever contacted from mocks or tests.
import { http, HttpResponse } from 'msw'
import { apiPattern } from '../../services/api/url.ts'
import { db, nowIso } from './db.ts'
import * as f from './fixtures.ts'
import { fail, jsonBody, num, ok, str, strList } from './reply.ts'

const p = apiPattern

const startJob = (mode: string, total: number) => {
  if (db.job.status === 'running') {
    return fail(409, 'A job is already running.', 'jobs.already_running')
  }
  db.job = { ...f.jobIdleFixture, mode, status: 'running', phase: 'fetching', round: 1,
    current: 0, total, started_at: nowIso(), logs: [`[mock] ${mode} started (${total})`] }
  return ok({ status: 'started', mode, symbols: total })
}

const jobs = [
  http.get(p('automate/status'), () => {
    // Each read advances a running mock job by one symbol, so progress is visible.
    const current = Number(db.job.current ?? 0)
    const total = Number(db.job.total ?? 0)
    if (db.job.status === 'running') {
      db.job = current + 1 >= total
        ? { ...db.job, current: total, status: 'done', phase: 'idle', finished_at: nowIso() }
        : { ...db.job, current: current + 1, current_symbol: `SYM${current + 1}` }
    }
    return ok(db.job)
  }),
  http.post(p('auto/start'), async ({ request }) => {
    const symbols = (await jsonBody(request)).symbols
    if (!Array.isArray(symbols) || symbols.length === 0) {
      return fail(400, 'No symbols provided.', 'jobs.no_symbols')
    }
    return startJob('auto', symbols.length)
  }),
  http.post(p('auto/start_all'), () => startJob('auto', f.symbolsFixture.count)),
  http.post(p('automate'), async ({ request }) => {
    const b = await jsonBody(request)
    const tfs = strList(b.timeframes).filter((t) => ['1h', '4h', '1d', '1w'].includes(t))
    if (tfs.length === 0) return fail(400, 'No valid timeframes. Use 1h, 4h, 1d, 1w.',
      'jobs.no_timeframes', { allowed: '1h, 4h, 1d, 1w' })
    if (!Array.isArray(b.symbols) || b.symbols.length === 0) {
      return fail(400, 'No symbols provided.', 'jobs.no_symbols')
    }
    return startJob('custom', b.symbols.length * tfs.length)
  }),
  http.post(p('auto/stop'), () => {
    if (db.job.status === 'running') {
      db.job = { ...db.job, status: 'stopped', phase: 'idle', finished_at: nowIso() }
    }
    return ok({ status: 'stopping' })
  }),
  http.post(p('tv/test'), () => ok(f.tvTestFixture)),
  http.post(p('data'), async ({ request }) => {
    const b = await jsonBody(request)
    if (!str(b.symbol) || !str(b.exchange)) return fail(422, 'symbol and exchange are required')
    return ok(f.barsFixture(str(b.symbol), Math.min(num(b.rows) || 40, 200)))
  }),
]

const file = (name: string, type: string, body: string) =>
  new HttpResponse(body, { headers: { 'Content-Type': type,
    'Content-Disposition': `attachment; filename=${name}` } })

const exportsAndGold = [
  http.get(p('export/check'), ({ request }) => {
    const list = new URL(request.url).searchParams.get('list_name') ?? ''
    const symbols = (db.watchlist[list] ?? []).map((i) => i.symbol)
    const missing = symbols.slice(-1)
    const total = list === 'All Symbols' ? f.symbolsFixture.count : symbols.length
    return ok({ total_in_list: total, available_count: total - missing.length,
      missing_count: missing.length, missing_symbols: list === 'All Symbols' ? [] : missing })
  }),
  http.get(p('export'), () => file('part.csv', 'text/csv', 'symbol,close\nAAPL,1\n')),
  http.get(p('export_zip'), () => file('export.zip', 'application/zip', 'PK mock')),
  http.get(p('export_formula'), () => file('ztrade_formula.csv', 'text/csv', 'name\nUIPT\n')),
  http.get(p('export_news'), () => file('ztrade_news.csv', 'text/csv', 'title\nmock\n')),
  http.get(p('gold/config'), () => ok(f.goldConfigFixture)),
  http.get(p('gold/models'), () => ok(f.goldModelsFixture)),
  http.get(p('gold/modes'), () => ok(f.goldModesFixture)),
  http.get(p('gold/price'), () => ok({ price: 4012.35 })),
  http.get(p('gold/status'), () => {
    if (db.gold.status === 'running') {
      db.gold = { ...db.gold, status: 'done', finished_at: nowIso(), message: 'mock done' }
    }
    return ok(db.gold)
  }),
  http.post(p('gold/analyze'), async ({ request }) => {
    const b = await jsonBody(request)
    return ok({ exchange: str(b.exchange), model: str(b.model), latest_price: 4012.35,
      analysis: '## Mock gold plan\n\n- Bias: neutral', generated_at: nowIso() })
  }),
  http.post(p('gold/automate'), async ({ request }) => {
    if (db.gold.status === 'running') {
      return fail(409, 'A gold job is already running.', 'gold.already_running')
    }
    const b = await jsonBody(request)
    db.gold = { ...f.goldJobFixture, status: 'running', started_at: nowIso() }
    return ok({ status: 'started', mode: 'gold', exchange: str(b.exchange) })
  }),
  http.post(p('gold/automate/stop'), () => {
    if (db.gold.status !== 'running') return ok({ detail: 'No job running' })
    db.gold = { ...db.gold, status: 'stopped' }
    return ok({ detail: 'Stop signal sent' })
  }),
  http.get(p('gold/export'), () => file('gold.zip', 'application/zip', 'PK mock')),
]

const scans = [
  http.post(p('stock_radar/scan'), async ({ request }) => {
    const b = await jsonBody(request)
    const symbols = Array.isArray(b.symbols)
      ? b.symbols.map((s) => str((s as Record<string, unknown>).symbol)) : []
    const analysis = `## Mock scan\n\n${symbols.join(', ')}`
    db.stockRadar = [{ id: db.stockRadar.length + 100, timestamp: nowIso(), symbols,
      formulas: strList(b.formulas), timeframes: strList(b.timeframes), extended_session: false,
      result_markdown: analysis }, ...db.stockRadar]
    return ok({ analysis, timestamp: nowIso() })
  }),
  http.post(p('earning_scan/scan'), async ({ request }) => {
    const symbols = strList((await jsonBody(request)).symbols)
    const results = symbols.map((symbol) => ({ symbol, provider: 'mock', history: [],
      next_earnings_date: null }))
    db.earning = [{ id: db.earning.length + 100, timestamp: nowIso(), symbols, results },
      ...db.earning]
    return ok({ results, timestamp: nowIso() })
  }),
]

export const jobHandlers = [...jobs, ...exportsAndGold, ...scans]
