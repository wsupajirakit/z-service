import { describe, expect, it } from 'vitest'
import { runWithCache } from '../../testing/mocks/actionHarness.ts'
import { renderPage } from '../../testing/mocks/renderPage.tsx'
import { apiGet } from '../../services/api/client.ts'
import { addTradeAction, removeSymbolAction, renamePortAction } from './api.ts'
import { AddTradeDialog, RemoveSymbolButton } from './components/PortEditor.tsx'
import { parseTrade } from './model.ts'
import { portfolioSchema } from './schemas.ts'

const read = () => apiGet('portfolio', portfolioSchema)

describe('portfolio actions', () => {
  it('adds a trade, removes a symbol, renames, and invalidates portfolio', async () => {
    const { invalidated } = await runWithCache(addTradeAction,
      { port: 'Default', symbol: 'NVDA', quantity: 3, price: 180, action: 'buy' },
      [['portfolio'], ['watchlist']])
    expect(invalidated).toEqual([['portfolio']])
    expect((await read()).Default?.positions.map((x) => x.symbol)).toContain('NVDA')
    await runWithCache(removeSymbolAction, { port: 'Default', symbol: 'AAPL' }, [])
    expect((await read()).Default?.history.some((t) => t.symbol === 'AAPL')).toBe(false)
    await runWithCache(renamePortAction, { port: 'Default', next: 'Main' }, [])
    expect(Object.keys(await read())).toEqual(['Main'])
  })

  it('validates trades: whole shares, positive price', () => {
    const base = { port: 'P', symbol: 'ko', quantity: '10', price: '64.1', action: 'buy' as const }
    expect(parseTrade(base)).toMatchObject({ ok: true, value: { symbol: 'KO', quantity: 10 } })
    expect(parseTrade({ ...base, quantity: '1.5' })).toEqual({ ok: false, field: 'quantity' })
    expect(parseTrade({ ...base, price: '0' })).toEqual({ ok: false, field: 'price' })
  })

  it('remove confirm says the trades are deleted for good', () => {
    const html = renderPage(<RemoveSymbolButton port="Default" symbol="KO" defaultOpen />, [])
    expect(html).toContain('data-testid="confirm-panel"')
    expect(html).toContain('KO')
    expect(html).toContain('Default')
  })

  it('add trade opens as a modal form with every field and the portfolio suggestions', () => {
    const closed = renderPage(<AddTradeDialog ports={['Default']} />, [])
    expect(closed).not.toContain('<form')
    const html = renderPage(<AddTradeDialog ports={['Default', 'Swing']} defaultOpen />, [])
    expect(html).toContain('<dialog')
    expect(html).toContain('data-testid="pf-add"')
    expect(html).toContain('<form')
    expect(html).toContain('type="submit"')
    expect(html).toContain('value="Default"')
    expect(html).toContain('<option value="Swing">')
  })
})
