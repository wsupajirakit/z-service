import { describe, expect, it } from 'vitest'
import { runWithCache } from '../../testing/mocks/actionHarness.ts'
import { renderPage } from '../../testing/mocks/renderPage.tsx'
import { earningHistoryQuery, earningScanAction } from './api.ts'
import { EarningScanForm } from './components/EarningScanForm.tsx'

describe('earning scan', () => {
  it('posts symbols and invalidates the history', async () => {
    const res = await runWithCache(earningScanAction, ['MSFT', 'KO'],
      [earningHistoryQuery.queryKey])
    expect(res.data.results.map((r) => r.symbol)).toEqual(['MSFT', 'KO'])
    expect(res.invalidated).toHaveLength(1)
  })

  it('confirm warns about paid data providers and shows the count', () => {
    const html = renderPage(<EarningScanForm defaultOpen initial={['MSFT', 'KO']} />, [])
    expect(html).toContain('data-testid="cost-warning"')
    expect(html).toContain('2')
  })
})
