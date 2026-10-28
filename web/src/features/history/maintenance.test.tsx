import { describe, expect, it } from 'vitest'
import { runWithCache } from '../../testing/mocks/actionHarness.ts'
import { renderPage } from '../../testing/mocks/renderPage.tsx'
import { apiGet } from '../../services/api/client.ts'
import { HistoryMaintenance } from './components/HistoryMaintenance.tsx'
import { cleanupAction, clearAllAction } from './maintenance.ts'
import { historyListSchema } from './schemas.ts'

describe('history maintenance', () => {
  it('cleanup sends hours, rejects out-of-range with detail, clear-all empties', async () => {
    const res = await runWithCache(cleanupAction, 24, [['history'], ['history', 42]])
    expect(res.data.message).toContain('24')
    expect(res.invalidated).toHaveLength(2)
    await expect(runWithCache(cleanupAction, 721, []))
      .rejects.toMatchObject({ detail: 'hours must be between 1 and 720.' })
    await runWithCache(clearAllAction, undefined, [])
    expect(await apiGet('history', historyListSchema)).toEqual([])
  })

  it('cleanup and clear each show a confirm step', () => {
    for (const step of ['cleanup', 'clear'] as const) {
      const html = renderPage(<HistoryMaintenance defaultOpen={step} />, [])
      expect(html).toContain('data-testid="confirm-panel"')
    }
  })
})
