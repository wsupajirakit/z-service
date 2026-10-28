import { describe, expect, it } from 'vitest'
import { runWithCache } from '../../testing/mocks/actionHarness.ts'
import { renderPage } from '../../testing/mocks/renderPage.tsx'
import { apiHref } from '../../services/api/url.ts'
import {
  analyzeAction, goldExportHref, goldJobQuery, startGoldAction, stopGoldAction,
} from './api.ts'
import { GoldJobPanel } from './components/GoldJobPanel.tsx'
import { safeExternalUrl } from './model.ts'

const run = { exchange: 'OANDA', model: 'mock-model-fast' }

describe('gold', () => {
  it('analyzes, starts and stops the server job', async () => {
    expect((await runWithCache(analyzeAction, run, [])).data.analysis).toContain('Mock')
    const start = await runWithCache(startGoldAction, run, [goldJobQuery.queryKey])
    expect(start.invalidated).toHaveLength(1)
    await expect(runWithCache(startGoldAction, run, [])).rejects.toMatchObject({ status: 409 })
    expect((await runWithCache(stopGoldAction, undefined, [])).data.detail)
      .toBe('Stop signal sent')
  })

  it('only https links are rendered; export href is same-origin', () => {
    expect(safeExternalUrl('https://drive.example/f/1')).toBe('https://drive.example/f/1')
    expect(safeExternalUrl('javascript:alert(1)')).toBeNull()
    expect(goldExportHref('swing', 'OANDA'))
      .toBe(`${apiHref('')}gold/export?mode=swing&exchange=OANDA`)
  })

  it('start asks for confirmation with the paid-provider warning', () => {
    const html = renderPage(<GoldJobPanel run={run} defaultOpen />,
      [[goldJobQuery.queryKey, { status: 'idle' }]])
    expect(html).toContain('data-testid="cost-warning"')
    expect(html).toContain('mock-model-fast')
  })
})
