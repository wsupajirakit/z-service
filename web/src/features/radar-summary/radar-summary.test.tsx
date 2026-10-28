import { describe, expect, it } from 'vitest'
import * as f from '../../testing/mocks/fixtures.ts'
import { renderPage } from '../../testing/mocks/renderPage.tsx'
import { roundDetailQuery, roundListQuery, roundStatusQuery, tfStatusQuery } from './api.ts'
import { RadarSummaryPage } from './components/RadarSummaryPage.tsx'
import { isRunning, pickStamp, tfRows } from './model.ts'
import * as s from './schemas.ts'

describe('radar summary', () => {
  const list = s.roundListSchema.parse(f.roundListFixture)
  const status = s.roundStatusSchema.parse(f.roundStatusFixture)
  const tf = s.tfStatusSchema.parse(f.tfStatusFixture)
  const detail = s.roundDetailSchema.parse(f.roundDetailFixture('20261023-1600'))

  it('model', () => {
    expect(tfRows(tf).map((r) => r.tf)).toEqual(['1W', '1D', '4H', '1H'])
    expect(isRunning(status)).toBe(false)
    expect(isRunning({ ...status, status: 'running' })).toBe(true)
    expect(pickStamp(['b', 'a'], null)).toBe('b')
    expect(pickStamp(['b'], 'old')).toBe('old')
    expect(pickStamp([], null)).toBeNull()
  })

  it('renders status, rounds and the digest as markdown without raw HTML', () => {
    const html = renderPage(<RadarSummaryPage stamp={null} onSelect={() => {}} />, [
      [roundListQuery.queryKey, list],
      [roundStatusQuery.queryKey, status],
      [tfStatusQuery.queryKey, tf],
      [roundDetailQuery('20261023-1600').queryKey, detail],
    ])
    expect(html).toContain('data-testid="round-list"')
    expect(html).toContain('<strong>AAPL</strong>')
    expect(html).not.toContain('<b>')
  })
})
