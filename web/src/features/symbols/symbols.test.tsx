import { describe, expect, it } from 'vitest'
import { symbolsFixture, versionFixture } from '../../testing/mocks/fixtures.ts'
import { renderPage } from '../../testing/mocks/renderPage.tsx'
import { versionSchema } from '../../services/api/common.ts'
import { symbolsQuery } from './api.ts'
import { OverviewPage } from './components/OverviewPage.tsx'
import { exchangeCounts } from './model.ts'
import { symbolsSchema } from './schemas.ts'

describe('symbols overview', () => {
  const info = symbolsSchema.parse(symbolsFixture)

  it('counts exchanges from the data', () => {
    expect(exchangeCounts(info)[0]).toEqual({ exchange: 'NASDAQ', count: 3 })
    expect(versionSchema.parse(versionFixture).version).toBe('0.9.0-mock')
  })

  it('renders version and counts', () => {
    const html = renderPage(<OverviewPage />, [[symbolsQuery.queryKey, info]])
    expect(html).toContain('data-testid="version-panel"')
    expect(html).toContain('data-testid="symbol-count"')
    expect(html).toContain('ZZZT')
  })
})
