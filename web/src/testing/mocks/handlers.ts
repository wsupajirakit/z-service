// MSW handlers for every endpoint the UI calls. Dev (`npm run dev:mock`) and tests share them,
// so no code path ever needs the real backend or its database. Reads come from the in-memory
// db (mocks/db.ts), which the write handlers change.
import { http } from 'msw'
import { apiPattern } from '../../services/api/url.ts'
import { db, portfolioView } from './db.ts'
import * as f from './fixtures.ts'
import { authHandlers } from './authHandlers.ts'
import { jobHandlers } from './jobHandlers.ts'
import { fail, ok } from './reply.ts'
import { writeHandlers } from './writeHandlers.ts'

const get = (path: string, body: () => Parameters<typeof ok>[0]) =>
  http.get(apiPattern(path), () => ok(body()))

const readHandlers = [
  get('version', () => f.versionFixture),
  get('settings/timezone', () => db.timezone),
  get('settings/destinations', () => db.destinations),
  get('settings/auto_skip_minutes', () => ({ minutes: db.autoSkip })),
  get('settings/tv_mode', () => ({ mode: db.tvMode })),
  get('settings/tv_token', () => db.tvToken),
  get('symbols', () => f.symbolsFixture),
  get('watchlist', () => db.watchlist),
  get('portfolio', () => portfolioView()),
  get('history', () => db.history),
  http.get(apiPattern('history/:id'), ({ params }) =>
    db.history.some((h) => h.id === Number(params.id))
      ? ok(f.historyDetailFixture)
      : fail(404, 'History record not found', 'history.not_found')),
  get('radar_round/list', () => ({ rounds: db.rounds })),
  get('radar_round/status', () => {
    // A mock round finishes on the first status read after it starts.
    if (db.roundStatus.status === 'running') db.roundStatus = { ...db.roundStatus, status: 'done' }
    return db.roundStatus
  }),
  get('radar_round/tf_status', () => f.tfStatusFixture),
  http.get(apiPattern('radar_round/:stamp'), ({ params }) =>
    db.rounds.some((r) => r.stamp === params.stamp)
      ? ok(f.roundDetailFixture(String(params.stamp)))
      : fail(404, `no round ${String(params.stamp)}`, 'radar.not_found',
        { stamp: String(params.stamp) })),
  get('stock_radar/history', () => db.stockRadar),
  get('earning_scan/history', () => db.earning),
]

export const handlers = [...readHandlers, ...authHandlers, ...writeHandlers, ...jobHandlers]
