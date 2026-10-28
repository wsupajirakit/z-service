import { describe, expect, it } from 'vitest'
import { stockRadarFixture } from '../../testing/mocks/fixtures.ts'
import { renderPage } from '../../testing/mocks/renderPage.tsx'
import { radarHistoryQuery } from './api.ts'
import { StockRadarPage } from './components/StockRadarPage.tsx'
import { formulaLabel } from './model.ts'
import { radarHistorySchema } from './schemas.ts'

describe('stock radar history', () => {
  it('labels formulas of any shape', () => {
    expect(formulaLabel('UIPT')).toBe('UIPT')
    expect(formulaLabel({ name: 'Core' })).toBe('Core')
    expect(formulaLabel(3)).toBe('3')
  })

  it('renders runs with markdown tables', () => {
    const runs = radarHistorySchema.parse(stockRadarFixture)
    const html = renderPage(<StockRadarPage />, [[radarHistoryQuery.queryKey, runs]])
    expect(html).toContain('data-testid="radar-run"')
    expect(html).toContain('<table')
  })
})
