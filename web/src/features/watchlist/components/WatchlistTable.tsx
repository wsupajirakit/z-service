import { m } from '../../../paraglide/messages.js'
import { useFormat } from '../../../hooks/useFormat.ts'
import { DataTable } from '../../../components/ui/DataTable.tsx'
import { Badge } from '../../../components/ui/Feedback.tsx'
import { filterRows, type WatchRow } from '../model.ts'
import { RemoveItemButton } from './ListEditor.tsx'

export function WatchlistTable({ data, list }: { data: WatchRow[]; list: string | null }) {
  const fmt = useFormat()
  return (
    <DataTable<WatchRow>
      testId="table"
      rows={data}
      rowKey={(r) => `${r.list}:${r.symbol}`}
      filterRows={(rows, q) => filterRows(rows, q, list)}
      searchPlaceholder={m.watchlist_search_placeholder()}
      columns={[
        { id: 'symbol', header: m.col_symbol(), value: (r) => r.symbol,
          cell: (r) => <span className="font-semibold">{r.symbol}</span> },
        { id: 'name', header: m.col_name(), value: (r) => r.name },
        { id: 'list', header: m.col_list(), value: (r) => r.list,
          cell: (r) => <Badge tone="secondary">{r.list}</Badge> },
        { id: 'added', header: m.col_added(), value: (r) => r.timestamp, noSearch: true,
          cell: (r) => <span className="text-muted-foreground">{fmt.dateTime(r.timestamp)}</span> },
        { id: 'actions', header: '', numeric: true,
          cell: (r) => <RemoveItemButton list={r.list} symbol={r.symbol} /> },
      ]}
    />
  )
}
