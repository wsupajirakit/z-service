import { describe, expect, it } from 'vitest'
import { watchlistFixture } from '../../testing/mocks/fixtures.ts'
import { renderPage } from '../../testing/mocks/renderPage.tsx'
import { watchlistQuery } from './api.ts'
import { WatchlistPage } from './components/WatchlistPage.tsx'
import { filterRows, listCounts, toRows } from './model.ts'
import { watchlistSchema } from './schemas.ts'

describe('watchlist', () => {
  const lists = watchlistSchema.parse(watchlistFixture)

  it('schema keeps unknown fields and accepts a null name', () => {
    const parsed = watchlistSchema.parse({ L: [{ symbol: 'X', name: null, extra: 1 }] })
    expect(parsed.L?.[0]).toMatchObject({ symbol: 'X', extra: 1 })
  })

  it('flattens, counts and filters', () => {
    const rows = toRows(lists)
    expect(rows).toHaveLength(5)
    expect(listCounts(lists)).toEqual([{ list: 'Defensive', count: 2 }, { list: 'Tech', count: 3 }])
    expect(filterRows(rows, 'micro', null).map((r) => r.symbol)).toEqual(['MSFT'])
    expect(filterRows(rows, '', 'Defensive')).toHaveLength(2)
  })

  it('renders list counts and rows', async () => {
    const html = renderPage(<WatchlistPage />, [[watchlistQuery.queryKey, lists]])
    expect(html).toContain('data-testid="list-counts"')
    expect(html).toContain('Tech (3)')
    expect(html).toContain('AAPL')
  })
})
