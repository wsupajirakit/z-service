import { describe, expect, it } from 'vitest'
import { runWithCache } from '../../testing/mocks/actionHarness.ts'
import { renderPage } from '../../testing/mocks/renderPage.tsx'
import { apiGet } from '../../services/api/client.ts'
import { deleteRoundAction, roundListQuery, roundStatusQuery, runRoundAction } from './api.ts'
import { DeleteRound, RunRound } from './components/RoundActions.tsx'
import { roundListSchema } from './schemas.ts'

describe('radar round actions', () => {
  it('runs a round (409 while running) and refreshes status + list', async () => {
    const first = await runWithCache(runRoundAction, { timeframes: ['1D'], newRecord: true },
      [roundStatusQuery.queryKey, roundListQuery.queryKey])
    expect(first.data.status).toBe('running')
    expect(first.invalidated).toHaveLength(2)
    await expect(runWithCache(runRoundAction, { timeframes: ['1D'], newRecord: false }, []))
      .rejects.toMatchObject({ status: 409 })
  })

  it('deletes a round; unknown stamp gives 404 detail', async () => {
    await runWithCache(deleteRoundAction, '20261022-1600', [])
    const list = await apiGet('radar_round/list', roundListSchema)
    expect(list.rounds.map((r) => r.stamp)).toEqual(['20261023-1600'])
    await expect(runWithCache(deleteRoundAction, 'nope', []))
      .rejects.toMatchObject({ detail: 'no round nope' })
  })

  it('both buttons confirm first', () => {
    const del = renderPage(<DeleteRound stamp="20261023-1600" defaultOpen />, [])
    expect(del).toContain('data-testid="confirm-panel"')
    expect(del).toContain('20261023-1600')
    const run = renderPage(<RunRound defaultOpen />,
      [[roundStatusQuery.queryKey, { status: 'done' }]])
    expect(run).toContain('data-testid="confirm-panel"')
  })
})
