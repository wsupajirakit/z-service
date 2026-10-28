import { describe, expect, it } from 'vitest'
import { earningScanFixture } from '../../testing/mocks/fixtures.ts'
import { renderPage } from '../../testing/mocks/renderPage.tsx'
import { earningHistoryQuery } from './api.ts'
import { EarningScanPage } from './components/EarningScanPage.tsx'
import { epsVerdict, latestQuarter, toNumber } from './model.ts'
import { earningHistorySchema } from './schemas.ts'

describe('earning scan history', () => {
  const runs = earningHistorySchema.parse(earningScanFixture)
  const [msft, ko, none] = runs[0]?.results ?? []

  it('reads numbers and numeric strings, judges beat/miss', () => {
    expect(toNumber('0.80')).toBe(0.8)
    expect(toNumber('')).toBeNull()
    expect(epsVerdict(latestQuarter(msft!))).toBe(1)
    expect(epsVerdict(latestQuarter(ko!))).toBe(-1)
    expect(latestQuarter(none!)).toBeNull()
  })

  it('renders each run', () => {
    const html = renderPage(<EarningScanPage />, [[earningHistoryQuery.queryKey, runs]])
    expect(html).toContain('data-testid="earning-run"')
    expect(html).toContain('MSFT')
  })
})
