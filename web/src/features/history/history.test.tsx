import { describe, expect, it } from 'vitest'
import { historyDetailFixture, historyListFixture } from '../../testing/mocks/fixtures.ts'
import { renderPage } from '../../testing/mocks/renderPage.tsx'
import { historyDetailQuery, historyListQuery } from './api.ts'
import { HistoryPage } from './components/HistoryPage.tsx'
import { filterHistory, recordColumns } from './model.ts'
import { historyDetailSchema, historyListSchema } from './schemas.ts'

describe('history', () => {
  const list = historyListSchema.parse(historyListFixture)
  const detail = historyDetailSchema.parse(historyDetailFixture)

  it('collects every record column once, in order', () => {
    expect(recordColumns([{ a: 1 }, { b: 2, a: 3 }])).toEqual(['a', 'b'])
    expect(recordColumns(detail)).toContain('RSI_14')
  })

  it('filters by ticker or exact timeframe', () => {
    expect(filterHistory(list, 'nv')).toHaveLength(1)
    expect(filterHistory(list, '1w').map((i) => i.symbol)).toEqual(['KO'])
  })

  it('renders the list and the selected detail', () => {
    const html = renderPage(<HistoryPage selectedId={42} onSelect={() => {}} />, [
      [historyListQuery.queryKey, list],
      [historyDetailQuery(42).queryKey, detail],
    ])
    expect(html).toContain('data-testid="history-list"')
    expect(html).toContain('data-testid="history-detail"')
    expect(html).toContain('EMA_20')
  })
})
