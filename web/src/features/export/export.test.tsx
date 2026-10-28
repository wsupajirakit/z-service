import { describe, expect, it } from 'vitest'
import { apiGet } from '../../services/api/client.ts'
import { apiHref } from '../../services/api/url.ts'
import { renderPage } from '../../testing/mocks/renderPage.tsx'
import { exportCheckQuery, exportLinks } from './api.ts'
import { ExportCheckView } from './components/ExportPage.tsx'
import { exportCheckSchema } from './schemas.ts'

describe('export', () => {
  it('builds same-origin download links; All Symbols sends no list_name', () => {
    const all = exportLinks('1d', 'All Symbols')
    // Relative to the API base: same-origin links, no host.
    const base = apiHref('')
    expect(all.map((l) => l.href.replace(base, ''))).toEqual([
      'export_zip?interval=1d', 'export?interval=1d&part=1', 'export?interval=1d&part=2',
      'export_zip?all=true', 'export_formula', 'export_news',
    ])
    expect(all.every((l) => l.href.startsWith(base) && !l.href.includes('//'))).toBe(true)
    expect(exportLinks('4h', 'My list')[0]?.href.replace(base, ''))
      .toBe('export_zip?interval=4h&list_name=My+list')
  })

  it('checks a list against the history', async () => {
    const c = await apiGet('export/check', exportCheckSchema,
      { query: { interval: '1d', list_name: 'Tech' } })
    expect(c).toMatchObject({ total_in_list: 3, missing_symbols: ['NVDA'] })
    const html = renderPage(<ExportCheckView interval="1d" list="Tech" />,
      [[exportCheckQuery('1d', 'Tech').queryKey, c]])
    expect(html).toContain('NVDA')
  })
})
