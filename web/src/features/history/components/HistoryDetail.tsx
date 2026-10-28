import { m } from '../../../paraglide/messages.js'
import { useFormat } from '../../../hooks/useFormat.ts'
import { Card, CardContent, CardHeader } from '../../../components/ui/Card.tsx'
import { DataTable } from '../../../components/ui/DataTable.tsx'
import { button } from '../../../components/ui/form.ts'
import { XIcon } from '../../../components/ui/icons.tsx'
import { QueryState } from '../../../components/ui/QueryState.tsx'
import type { CellValue } from '../../../utils/table.ts'
import { useHistoryDetail } from '../api.ts'
import { recordColumns } from '../model.ts'
import type { HistoryRecord } from '../schemas.ts'

const sortable = (v: unknown): CellValue =>
  (typeof v === 'number' || typeof v === 'string' || typeof v === 'boolean' ? v : null)

export function HistoryDetail({ id, onClose }: { id: number; onClose?: () => void }) {
  const query = useHistoryDetail(id)
  const fmt = useFormat()
  return (
    <Card testId="history-detail">
      <CardHeader
        title={m.history_detail_title({ id })}
        actions={onClose && (
          <button type="button" className={button('ghost', 'icon-sm')}
            aria-label={m.dialog_close()} onClick={onClose}>
            <XIcon />
          </button>
        )}
      />
      <CardContent>
        <QueryState query={query} isEmpty={(d) => d.length === 0}>
          {(records) => (
            <DataTable<HistoryRecord>
              rows={records}
              rowKey={(_, i) => String(i)}
              columns={recordColumns(records).map((key) => ({
                id: key,
                header: key,
                numeric: typeof records[0]?.[key] === 'number',
                value: (r) => sortable(r[key]),
                cell: (r) => fmt.cell(r[key]),
              }))}
            />
          )}
        </QueryState>
      </CardContent>
    </Card>
  )
}
