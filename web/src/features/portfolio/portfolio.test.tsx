import { describe, expect, it } from 'vitest'
import { portfolioFixture } from '../../testing/mocks/fixtures.ts'
import { renderPage } from '../../testing/mocks/renderPage.tsx'
import { portfolioQuery } from './api.ts'
import { PortfolioPage } from './components/PortfolioPage.tsx'
import { costBasis, summarize } from './model.ts'
import { portfolioSchema } from './schemas.ts'

describe('portfolio', () => {
  const ports = portfolioSchema.parse(portfolioFixture)

  it('computes cost basis and sorts trades newest first', () => {
    const [first] = summarize(ports)
    expect(first?.cost).toBeCloseTo(10 * 221.5 + 20 * 64.1)
    expect(costBasis([])).toBe(0)
    expect(first?.trades[0]?.action).toBe('sell')
  })

  it('renders positions', () => {
    const html = renderPage(<PortfolioPage />, [[portfolioQuery.queryKey, ports]])
    expect(html).toContain('data-testid="port"')
    expect(html).toContain('KO')
  })
})
