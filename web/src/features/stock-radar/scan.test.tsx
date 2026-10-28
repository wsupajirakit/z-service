import { describe, expect, it } from 'vitest'
import { symbolsFixture } from '../../testing/mocks/fixtures.ts'
import { runWithCache } from '../../testing/mocks/actionHarness.ts'
import { renderPage } from '../../testing/mocks/renderPage.tsx'
import { symbolsQuery } from '../../services/api/lists.ts'
import { radarHistoryQuery, scanAction } from './api.ts'
import { ScanForm } from './components/ScanForm.tsx'

describe('stock radar scan', () => {
  it('posts the scan and invalidates the history', async () => {
    const res = await runWithCache(scanAction, {
      targets: [{ symbol: 'NVDA', exchange: 'NASDAQ' }], formulas: ['UIPT'], timeframes: ['1D'],
      extended: false, mode: 'ai',
    }, [radarHistoryQuery.queryKey])
    expect(res.data.analysis).toContain('NVDA')
    expect(res.invalidated).toHaveLength(1)
  })

  it('AI mode confirm warns about paid providers', () => {
    const html = renderPage(<ScanForm defaultOpen />, [[symbolsQuery.queryKey, symbolsFixture]])
    expect(html).toContain('data-testid="confirm-panel"')
    expect(html).toContain('data-testid="cost-warning"')
  })
})
