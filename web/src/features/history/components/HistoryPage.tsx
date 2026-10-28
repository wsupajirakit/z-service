import { m } from '../../../paraglide/messages.js'
import { useFormat } from '../../../hooks/useFormat.ts'
import { Card, CardContent } from '../../../components/ui/Card.tsx'
import { DataTable } from '../../../components/ui/DataTable.tsx'
import { Badge } from '../../../components/ui/Feedback.tsx'
import { button } from '../../../components/ui/form.ts'
import { PageHeader } from '../../../components/ui/PageHeader.tsx'
import { QueryState } from '../../../components/ui/QueryState.tsx'
import { useHistoryList } from '../api.ts'
import { filterHistory } from '../model.ts'
import type { HistoryItem } from '../schemas.ts'
import { HistoryDetail } from './HistoryDetail.tsx'
import { HistoryMaintenance } from './HistoryMaintenance.tsx'

type Props = { selectedId: number | null; onSelect: (id: number | null) => void }

export function HistoryPage({ selectedId, onSelect }: Props) {
  const query = useHistoryList()
  const fmt = useFormat()
  return (
    <section className="space-y-6">
      <PageHeader description={m.page_desc_history()} />
      <Card>
        <CardContent className="pt-5">
          <QueryState query={query}>
            {(items) => (
              <DataTable<HistoryItem>
                testId="history-list"
                rows={items}
                rowKey={(r) => String(r.id)}
                filterRows={filterHistory}
                searchPlaceholder={m.history_search_placeholder()}
                columns={[
                  { id: 'time', header: m.col_time(), value: (r) => r.timestamp,
                    cell: (r) => fmt.dateTime(r.timestamp) },
                  { id: 'symbol', header: m.col_symbol(), value: (r) => r.symbol,
                    cell: (r) => <span className="font-semibold">{r.symbol}</span> },
                  { id: 'exchange', header: m.col_exchange(), value: (r) => r.exchange ?? '' },
                  { id: 'interval', header: m.col_interval(), value: (r) => r.interval,
                    cell: (r) => <Badge tone="outline">{r.interval}</Badge> },
                  { id: 'ext', header: m.col_extended(), value: (r) => r.extended_session,
                    cell: (r) => (r.extended_session ? m.yes() : m.no()) },
                  { id: 'open', header: '', numeric: true, cell: (r) => (
                    <button type="button" className={button(
                      selectedId === r.id ? 'secondary' : 'ghost', 'sm')}
                    aria-pressed={selectedId === r.id} onClick={() => onSelect(r.id)}>
                      {selectedId === r.id ? m.action_selected() : m.action_view()}
                    </button>
                  ) },
                ]}
              />
            )}
          </QueryState>
        </CardContent>
      </Card>
      {selectedId !== null && <HistoryDetail id={selectedId} onClose={() => onSelect(null)} />}
      <HistoryMaintenance />
    </section>
  )
}
