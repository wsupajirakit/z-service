import { describe, expect, it } from 'vitest'
import { jobIdleFixture } from '../../testing/mocks/fixtures.ts'
import { runWithCache } from '../../testing/mocks/actionHarness.ts'
import { renderPage } from '../../testing/mocks/renderPage.tsx'
import { apiGet } from '../../services/api/client.ts'
import { appConfig } from '../../config/app.ts'
import {
  customRunAction, fetchDataAction, jobQuery, startAllAction, startAutoAction, stopAction,
  tvTestAction,
} from './api.ts'
import { StopJob } from './components/JobStatus.tsx'
import { barColumns, jobPollMs, progressPct } from './model.ts'
import { jobSchema } from './schemas.ts'

const job = (over: object) => jobSchema.parse({ ...jobIdleFixture, ...over })
const targets = [{ symbol: 'AAPL', exchange: 'NASDAQ' }]

describe('jobs', () => {
  it('polls fast only while running and computes progress', () => {
    expect(jobPollMs(job({ status: 'running' }))).toBe(appConfig.poll.jobRunning)
    expect(jobPollMs(job({ status: 'idle' }))).toBe(appConfig.poll.jobIdle)
    expect(progressPct(job({ current: 1, total: 4 }))).toBe(25)
    expect(barColumns([{ x: 1, close: 2, datetime: 'd' }])).toEqual(['datetime', 'close', 'x'])
  })

  it('starts, refuses a second start (409 detail), and stops', async () => {
    const first = await runWithCache(startAutoAction, { targets, rows: 80, forceAllTf: false },
      [jobQuery.queryKey])
    expect(first.data).toMatchObject({ status: 'started', mode: 'auto', symbols: 1 })
    expect(first.invalidated).toHaveLength(1)
    await expect(runWithCache(startAllAction, undefined, []))
      .rejects.toMatchObject({ status: 409, detail: 'A job is already running.' })
    await runWithCache(stopAction, undefined, [])
    expect((await apiGet('automate/status', jobSchema)).status).toBe('stopped')
  })

  it('custom run validates timeframes on the server', async () => {
    await expect(runWithCache(customRunAction,
      { timeframes: ['5m'], targets, rows: 80, extended: false }, []))
      .rejects.toMatchObject({ status: 400 })
    const ok = await runWithCache(customRunAction,
      { timeframes: ['1d', '1w'], targets, rows: 80, extended: false }, [])
    expect(ok.data.mode).toBe('custom')
  })

  it('tv test and single fetch return parsed results', async () => {
    expect((await runWithCache(tvTestAction, undefined, [])).data.ok).toBe(true)
    const bars = await runWithCache(fetchDataAction,
      { symbol: 'KO', exchange: 'NYSE', interval: '1d', rows: 5, extended: false }, [['history']])
    expect(bars.data).toHaveLength(5)
    expect(bars.invalidated).toEqual([['history']])
  })

  it('stop asks for confirmation', () => {
    const html = renderPage(<StopJob job={job({ status: 'running', mode: 'auto' })}
      defaultOpen />, [])
    expect(html).toContain('data-testid="confirm-panel"')
  })
})
