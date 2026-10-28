// The one table component: search box, sortable headers, pagination, empty state.
// Logic lives in utils/table.ts (pure, tested); this file only renders it.
import { useState, type ReactNode } from 'react'
import { m } from '../../paraglide/messages.js'
import { appConfig } from '../../config/app.ts'
import { nextSort, paginate, searchRows, sortRows, type CellValue, type Sort } from
  '../../utils/table.ts'
import { cn } from './cn.ts'
import { EmptyState } from './Feedback.tsx'
import { button, searchInputClass, selectSmClass } from './form.ts'
import {
  ArrowDownIcon, ArrowUpIcon, ChevronLeftIcon, ChevronRightIcon, ChevronsUpDownIcon, SearchIcon,
} from './icons.tsx'

export type Column<T> = {
  id: string
  header: string
  /** Sort key, search text and default cell text. A column without it is not sortable. */
  value?: (row: T) => CellValue
  cell?: (row: T) => ReactNode
  numeric?: boolean
  /** Leave the column out of the text search (e.g. dates, numbers). */
  noSearch?: boolean
}

type Props<T> = {
  columns: Column<T>[]
  rows: readonly T[]
  rowKey: (row: T, index: number) => string
  testId?: string
  /** Replaces the default "contains" search (pages with their own matching rules). */
  filterRows?: (rows: readonly T[], query: string) => T[]
  searchPlaceholder?: string
  /** Extra controls next to the search box. */
  toolbar?: ReactNode
  initialSort?: Sort
  /** Off for tiny fixed lists; search is on by default. */
  search?: boolean
}

const { pageSizes, pageSize: defaultPageSize } = appConfig.table

function SortMark({ dir }: { dir: 'asc' | 'desc' | null }) {
  if (dir === 'asc') return <ArrowUpIcon size={14} />
  if (dir === 'desc') return <ArrowDownIcon size={14} />
  return <ChevronsUpDownIcon size={14} className="opacity-40" />
}

function HeaderCell<T>({ column, sort, onSort }: {
  column: Column<T>
  sort: Sort
  onSort: (id: string) => void
}) {
  const dir = sort?.id === column.id ? (sort.desc ? 'desc' : 'asc') : null
  const align = column.numeric ? 'text-right' : 'text-left'
  const ariaSort = dir === 'asc' ? 'ascending' : dir === 'desc' ? 'descending' : undefined
  return (
    <th scope="col" aria-sort={ariaSort}
      className={cn('h-10 px-3 font-medium whitespace-nowrap text-muted-foreground', align)}>
      {column.value && column.header ? (
        <button type="button" onClick={() => onSort(column.id)}
          className={cn('-mx-2 inline-flex items-center gap-1 rounded-md px-2 py-1',
            'hover:bg-accent hover:text-accent-foreground', column.numeric && 'flex-row-reverse')}>
          {column.header}
          <SortMark dir={dir} />
        </button>
      ) : column.header}
    </th>
  )
}

function Pagination({ from, to, total, pageIndex, pageCount, pageSize, onPage, onSize }: {
  from: number; to: number; total: number; pageIndex: number; pageCount: number
  pageSize: number; onPage: (index: number) => void; onSize: (size: number) => void
}) {
  return (
    <div className="flex flex-wrap items-center justify-end gap-x-6 gap-y-2 border-t px-3 py-2
      text-sm text-muted-foreground" data-testid="table-pagination">
      <label className="flex items-center gap-2">
        {m.table_rows_per_page()}
        <select className={selectSmClass} value={pageSize}
          onChange={(e) => onSize(Number(e.target.value))}>
          {pageSizes.map((n) => <option key={n} value={n}>{n}</option>)}
        </select>
      </label>
      <span className="tabular-nums" data-testid="table-range">
        {m.table_range({ from, to, total })}
      </span>
      <span className="flex gap-1">
        <button type="button" className={button('outline', 'icon-sm')}
          aria-label={m.table_prev()} disabled={pageIndex === 0}
          onClick={() => onPage(pageIndex - 1)}>
          <ChevronLeftIcon />
        </button>
        <button type="button" className={button('outline', 'icon-sm')}
          aria-label={m.table_next()} disabled={pageIndex >= pageCount - 1}
          onClick={() => onPage(pageIndex + 1)}>
          <ChevronRightIcon />
        </button>
      </span>
    </div>
  )
}

function useTableState<T>({ columns, rows, filterRows, initialSort }: Props<T>) {
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState<Sort>(initialSort ?? null)
  const [pageIndex, setPageIndex] = useState(0)
  const [pageSize, setPageSize] = useState<number>(defaultPageSize)
  // Recomputed each render on purpose: callers pass columns inline and the lists are a few
  // hundred rows at most, so a memo would never hit and only add noise.
  const texts = (row: T) => columns.filter((c) => c.value && !c.noSearch)
    .map((c) => c.value?.(row))
  const found = filterRows ? filterRows(rows, query) : searchRows(rows, query, texts)
  const by = columns.find((c) => c.id === sort?.id)?.value
  const sorted = by && sort ? sortRows(found, by, sort.desc) : found
  return {
    query, sort, pageSize, page: paginate(sorted, pageIndex, pageSize),
    search: (q: string) => { setQuery(q); setPageIndex(0) },
    sortBy: (id: string) => { setSort(nextSort(sort, id)); setPageIndex(0) },
    setPageIndex,
    resize: (size: number) => { setPageSize(size); setPageIndex(0) },
  }
}

export function DataTable<T>(props: Props<T>) {
  const { columns, rowKey, testId, searchPlaceholder, toolbar, search = true } = props
  const t = useTableState(props)
  return (
    <div className="space-y-3">
      {(search || toolbar) && (
        <div className="flex flex-wrap items-center gap-2">
          {search && (
            <label className="relative w-full max-w-xs">
              <span className="sr-only">{m.search_label()}</span>
              <SearchIcon className="pointer-events-none absolute top-2.5 left-2.5
                text-muted-foreground" />
              <input type="search" className={searchInputClass} value={t.query}
                placeholder={searchPlaceholder ?? m.table_search_placeholder()}
                onChange={(e) => t.search(e.target.value)} data-testid="table-search" />
            </label>
          )}
          {toolbar}
        </div>
      )}
      <div className="overflow-hidden rounded-lg border bg-card">
        <div className="overflow-x-auto">
          <table className="w-full caption-bottom text-sm" data-testid={testId}>
            <thead className="border-b bg-muted/50">
              <tr>
                {columns.map((c) => <HeaderCell key={c.id} column={c} sort={t.sort}
                  onSort={t.sortBy} />)}
              </tr>
            </thead>
            <tbody>
              {t.page.rows.map((row, i) => (
                <tr key={rowKey(row, t.page.from - 1 + i)} data-row={t.page.from - 1 + i}
                  className="border-b transition-colors last:border-0 hover:bg-muted/40">
                  {columns.map((c) => (
                    <td key={c.id} className={cn('h-10 px-3 py-1.5 align-middle',
                      c.numeric && 'text-right tabular-nums')}>
                      {c.cell ? c.cell(row) : String(c.value?.(row) ?? '')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {t.page.total === 0 && (
          <div className="p-4">
            <EmptyState title={t.query ? m.table_no_results() : m.state_empty()} />
          </div>
        )}
        <Pagination from={t.page.from} to={t.page.to} total={t.page.total}
          pageIndex={t.page.pageIndex} pageCount={t.page.pageCount} pageSize={t.pageSize}
          onPage={t.setPageIndex} onSize={t.resize} />
      </div>
    </div>
  )
}
