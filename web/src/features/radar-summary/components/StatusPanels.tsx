import { m } from '../../../paraglide/messages.js'
import { serverText } from '../../../services/api/serverMessages.ts'
import { enumLabel } from '../../../i18n/enums.ts'
import { useFormat } from '../../../hooks/useFormat.ts'
import { Badge, type Tone } from '../../../components/ui/Feedback.tsx'
import { DataTable } from '../../../components/ui/DataTable.tsx'
import { QueryState } from '../../../components/ui/QueryState.tsx'
import { useRoundStatus, useTfStatus } from '../api.ts'
import { tfRows, type TfRow } from '../model.ts'

const tone = (status: string | null | undefined): Tone =>
  status === 'running' ? 'success' : status === 'error' ? 'destructive' : 'secondary'

export function RoundStatusLine() {
  const query = useRoundStatus()
  const fmt = useFormat()
  return (
    <QueryState query={query}>
      {(s) => (
        <div className="flex flex-wrap items-center gap-2 text-sm" data-testid="round-status">
          <Badge tone={tone(s.status)}>{enumLabel('status', s.status)}</Badge>
          <span className="text-muted-foreground">
            {m.radar_status({
              status: enumLabel('status', s.status),
              phase: s.phase ? enumLabel('phase', s.phase) : '',
              message: serverText({
                code: s.message_code, params: s.message_params, text: s.message,
              }),
            })}
            {s.finished_at ? ` · ${fmt.dateTime(s.finished_at)}` : ''}
          </span>
          {s.error ? <span className="text-destructive">{s.error}</span> : null}
        </div>
      )}
    </QueryState>
  )
}

export function TfStatusTable() {
  const query = useTfStatus()
  const fmt = useFormat()
  return (
    <QueryState query={query}>
      {(status) => (
        <DataTable<TfRow>
          testId="tf-status"
          search={false}
          rows={tfRows(status)}
          rowKey={(r) => r.tf}
          columns={[
            { id: 'tf', header: m.col_timeframe(), value: (r) => r.tf,
              cell: (r) => <Badge tone="outline">{r.tf}</Badge> },
            { id: 'count', header: m.col_symbols(), numeric: true, value: (r) => r.symbols_count,
              cell: (r) => fmt.number(r.symbols_count, 0) },
            { id: 'max', header: m.col_fetched_at(), value: (r) => r.fetched_at_max,
              cell: (r) => fmt.dateTime(r.fetched_at_max) },
            { id: 'dup', header: m.col_duplicates(), numeric: true,
              value: (r) => r.duplicate_symbols ?? 0,
              cell: (r) => fmt.number(r.duplicate_symbols ?? 0, 0) },
          ]}
        />
      )}
    </QueryState>
  )
}
