import { describe, expect, it } from 'vitest'
import { runWithCache } from '../../testing/mocks/actionHarness.ts'
import { renderPage } from '../../testing/mocks/renderPage.tsx'
import { apiGet } from '../../services/api/client.ts'
import { watchlistSchema } from '../../services/api/lists.ts'
import { addItemAction, removeItemAction, renameListAction } from './api.ts'
import { AddItemDialog, RemoveItemButton } from './components/ListEditor.tsx'
import { parseAddItem } from './model.ts'

const read = () => apiGet('watchlist', watchlistSchema)

describe('watchlist actions', () => {
  it('adds with exchange and invalidates watchlist + symbols', async () => {
    const { invalidated } = await runWithCache(addItemAction,
      { list: 'Tech', symbol: 'AMD', name: 'AMD', exchange: 'NASDAQ' },
      [['watchlist'], ['symbols'], ['portfolio']])
    expect(invalidated).toEqual([['watchlist'], ['symbols']])
    expect((await read()).Tech?.find((i) => i.symbol === 'AMD')?.exchange).toBe('NASDAQ')
  })

  it('removes a symbol and renames a list', async () => {
    await runWithCache(removeItemAction, { list: 'Tech', symbol: 'AAPL' }, [])
    expect((await read()).Tech?.map((i) => i.symbol)).not.toContain('AAPL')
    await runWithCache(renameListAction, { list: 'Tech', next: 'Chips' }, [])
    const lists = await read()
    expect(Object.keys(lists).sort()).toEqual(['Chips', 'Defensive'])
  })

  it('rename to an empty name returns the server detail', async () => {
    await expect(runWithCache(renameListAction, { list: 'Tech', next: ' ' }, []))
      .rejects.toMatchObject({ status: 400, detail: 'Invalid name' })
  })

  it('validates the add form', () => {
    expect(parseAddItem({ list: 'L', symbol: 'brk.b', name: '', exchange: '' }))
      .toEqual({ ok: true, value: { list: 'L', symbol: 'BRK.B', name: 'BRK.B', exchange: null } })
    expect(parseAddItem({ list: 'L', symbol: 'A', name: '', exchange: 'N Y' }))
      .toEqual({ ok: false, field: 'exchange' })
  })

  it('remove asks for confirmation naming the symbol and list', () => {
    const html = renderPage(<RemoveItemButton list="Tech" symbol="NVDA" defaultOpen />, [])
    expect(html).toContain('data-testid="confirm-panel"')
    expect(html).toContain('NVDA')
    expect(html).toContain('Tech')
  })

  it('add symbol opens as a modal form prefilled with the shown list', () => {
    const lists = { Tech: [], Defensive: [] }
    const closed = renderPage(<AddItemDialog lists={lists} list="Tech" />, [])
    expect(closed).not.toContain('<form')
    const html = renderPage(<AddItemDialog lists={lists} list="Tech" defaultOpen />, [])
    expect(html).toContain('data-testid="wl-add"')
    expect(html).toContain('<form')
    expect(html).toContain('value="Tech"')
    expect(html).toContain('<option value="Defensive">')
  })
})
