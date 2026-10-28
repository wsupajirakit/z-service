import { queryOptions, useQuery } from '@tanstack/react-query'
import { apiGet } from '../../services/api/client.ts'
import { apiHref } from '../../services/api/url.ts'
import { domainConfig } from '../../config/domain.ts'
import { exportCheckSchema } from './schemas.ts'

export const exportCheckQuery = (interval: string, list: string) => queryOptions({
  queryKey: ['export', 'check', interval, list],
  queryFn: ({ signal }) => apiGet('export/check', exportCheckSchema, {
    query: { interval, list_name: list }, signal,
  }),
})
export const useExportCheck = (interval: string, list: string) =>
  useQuery(exportCheckQuery(interval, list))

/** `list_name` is omitted for "All Symbols", as legacy does. */
const listParam = (list: string) =>
  list === domainConfig.domain.allSymbolsList ? undefined : list

export type DownloadLink = { id: string; href: string; file: string }

export function exportLinks(interval: string, list: string): DownloadLink[] {
  const list_name = listParam(list)
  return [
    { id: 'zip', file: `ztrade_export_${interval}.zip`,
      href: apiHref('export_zip', { interval, list_name }) },
    { id: 'part1', file: `ztrade_export_${interval}_part1.csv`,
      href: apiHref('export', { interval, part: 1, list_name }) },
    { id: 'part2', file: `ztrade_export_${interval}_part2.csv`,
      href: apiHref('export', { interval, part: 2, list_name }) },
    { id: 'all', file: 'ztrade_export_all.zip',
      href: apiHref('export_zip', { all: true, list_name }) },
    { id: 'formula', file: 'ztrade_formula.csv', href: apiHref('export_formula') },
    { id: 'news', file: 'ztrade_news.csv', href: apiHref('export_news') },
  ]
}
