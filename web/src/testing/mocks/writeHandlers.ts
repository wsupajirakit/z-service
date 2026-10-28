// Stateful write endpoints: watchlist, portfolio, settings, history, radar rounds.
// Validation mirrors the backend routes (same status codes and `detail` texts).
import { http } from 'msw'
import { apiPattern } from '../../services/api/url.ts'
import { db, nowIso } from './db.ts'
import { fail, jsonBody, num, ok, str } from './reply.ts'

const p = apiPattern

const watchlist = [
  http.post(p('watchlist'), async ({ request }) => {
    const b = await jsonBody(request)
    const list = str(b.list_name) || 'Default'
    const symbol = str(b.symbol).toUpperCase()
    if (!symbol) return fail(422, 'symbol is required')
    const items = (db.watchlist[list] ??= [])
    const exchange = str(b.exchange).toUpperCase() || null
    const item = { symbol, name: str(b.name) || symbol, exchange, timestamp: nowIso() }
    db.watchlist[list] = [...items.filter((i) => i.symbol !== symbol), item]
    return ok({ status: 'ok' })
  }),
  http.delete(p('watchlist/:list/:symbol'), ({ params }) => {
    const list = String(params.list)
    db.watchlist[list] = (db.watchlist[list] ?? []).filter((i) => i.symbol !== params.symbol)
    if (db.watchlist[list]?.length === 0) delete db.watchlist[list]
    return ok({ status: 'ok' })
  }),
  http.put(p('watchlist/:list'), async ({ params, request }) => {
    const next = str((await jsonBody(request)).new_name).trim()
    if (!next) return fail(400, 'Invalid name', 'lists.invalid_name')
    const list = String(params.list)
    const items = db.watchlist[list] ?? []
    delete db.watchlist[list]
    db.watchlist[next] = [...(db.watchlist[next] ?? []), ...items]
    return ok({ status: 'ok' })
  }),
]

const portfolio = [
  http.post(p('portfolio'), async ({ request }) => {
    const b = await jsonBody(request)
    const port = str(b.port_name) || 'Default'
    const quantity = num(b.quantity)
    const price = num(b.buy_price)
    if (!Number.isInteger(quantity) || !(price > 0)) return fail(422, 'bad quantity or price')
    ;(db.trades[port] ??= []).push({ symbol: str(b.symbol).toUpperCase(), quantity,
      buy_price: price, timestamp: nowIso(), action: str(b.action) || 'buy' })
    return ok({ status: 'ok' })
  }),
  http.delete(p('portfolio/:port/:symbol'), ({ params }) => {
    const port = String(params.port)
    db.trades[port] = (db.trades[port] ?? []).filter((t) => t.symbol !== params.symbol)
    return ok({ status: 'ok' })
  }),
  http.put(p('portfolio/:port'), async ({ params, request }) => {
    const next = str((await jsonBody(request)).new_name).trim()
    if (!next) return fail(400, 'Invalid name', 'lists.invalid_name')
    const rows = db.trades[String(params.port)] ?? []
    delete db.trades[String(params.port)]
    db.trades[next] = [...(db.trades[next] ?? []), ...rows]
    return ok({ status: 'ok' })
  }),
]

const settings = [
  http.post(p('settings/timezone'), async ({ request }) => {
    const b = await jsonBody(request)
    const offset = num(b.offset_minutes)
    if (!(offset >= -720 && offset <= 840)) {
      return fail(400, 'offset_minutes must be between -720 and 840.',
        'settings.offset_range', { min: -720, max: 840 })
    }
    db.timezone = { offset_minutes: offset, label: str(b.label) }
    return ok(db.timezone)
  }),
  http.post(p('settings/destinations'), async ({ request }) => {
    const b = await jsonBody(request)
    for (const key of Object.keys(db.destinations) as (keyof typeof db.destinations)[]) {
      if (typeof b[key] === 'boolean') db.destinations[key] = b[key]
    }
    return ok(db.destinations)
  }),
  http.post(p('settings/auto_skip_minutes'), async ({ request }) => {
    const minutes = num((await jsonBody(request)).minutes)
    if (!(minutes >= 1 && minutes <= 100)) return fail(400, 'Minutes must be between 1 and 100',
      'settings.minutes_range', { min: 1, max: 100 })
    db.autoSkip = minutes
    return ok({ minutes })
  }),
  http.post(p('settings/tv_mode'), async ({ request }) => {
    const mode = num((await jsonBody(request)).mode)
    if (![1, 2, 3].includes(mode)) return fail(400, 'Mode must be 1, 2, or 3', 'tv.invalid_mode')
    db.tvMode = mode
    db.tvToken = { status: 'none' }
    return ok({ mode })
  }),
  http.post(p('settings/tv_token'), async ({ request }) => {
    const token = str((await jsonBody(request)).token).trim()
    if (!token) return fail(400, 'Token cannot be empty', 'tv.token_empty')
    if (token === 'expired') return fail(400, 'Token is already expired', 'tv.token_expired')
    db.tvToken = { status: 'active', expires_in_minutes: 59.5 }
    return ok(db.tvToken)
  }),
]


const history = [
  http.post(p('history/cleanup'), ({ request }) => {
    const hours = Number(new URL(request.url).searchParams.get('hours') ?? 2)
    if (!(hours >= 1 && hours <= 720)) return fail(400, 'hours must be between 1 and 720.',
      'history.hours_range', { min: 1, max: 720 })
    const deleted = db.history.length > 1 ? 1 : 0
    db.history = db.history.slice(0, db.history.length - deleted)
    return ok({ status: 'success', deleted, kept: db.history.length,
      message: `deleted ${deleted} rows older than ${hours} h (mock)` })
  }),
  http.delete(p('history'), () => {
    db.history = []
    return ok({ status: 'success', message: 'History cleared' })
  }),
]

const rounds = [
  http.post(p('radar_round/run'), async ({ request }) => {
    if (db.roundStatus.status === 'running') {
      return fail(409, 'A radar round is already running (started mock).',
        'radar.already_running', { started_at: 'mock' })
    }
    const b = await jsonBody(request)
    const stamp = `2026${String(1100 + db.rounds.length)}-1600`
    const base = db.rounds[0]
    if (base) db.rounds = [{ ...base, id: base.id + 1, stamp, created_at: nowIso() }, ...db.rounds]
    db.roundStatus = { status: 'running', phase: 'screen', message: 'mock round',
      timeframes: b.timeframes ?? null, stamp, started_at: nowIso(), finished_at: null }
    return ok(db.roundStatus)
  }),
  http.delete(p('radar_round/:stamp'), ({ params }) => {
    const stamp = String(params.stamp)
    if (!db.rounds.some((r) => r.stamp === stamp)) {
      return fail(404, `no round ${stamp}`, 'radar.not_found', { stamp })
    }
    db.rounds = db.rounds.filter((r) => r.stamp !== stamp)
    return ok({ status: 'deleted', stamp })
  }),
]

export const writeHandlers = [
  ...watchlist, ...portfolio, ...settings, ...history, ...rounds,
]
