import { m } from '../../../paraglide/messages.js'
import { useFormat } from '../../../hooks/useFormat.ts'
import { DataTable } from '../../../components/ui/DataTable.tsx'
import { Badge } from '../../../components/ui/Feedback.tsx'
import { button } from '../../../components/ui/form.ts'
import { QueryState } from '../../../components/ui/QueryState.tsx'
import { useRoundList } from '../api.ts'
import type { RoundMeta } from '../schemas.ts'

type Props = { selected: string | null; onSelect: (stamp: string) => void }

export function RoundList({ selected, onSelect }: Props) {
  const query = useRoundList()
  const fmt = useFormat()
  return (
    <QueryState query={query}>
      {({ rounds }) => (
        <DataTable<RoundMeta>
          testId="round-list"
          rows={rounds}
          rowKey={(r) => r.stamp}
          columns={[
            { id: 'stamp', header: m.col_round(), value: (r) => r.stamp, cell: (r) => (
              <button type="button" aria-pressed={r.stamp === selected}
                className={button(r.stamp === selected ? 'secondary' : 'link', 'sm')}
                onClick={() => onSelect(r.stamp)}>
                {r.stamp}
              </button>
            ) },
            { id: 'asof', header: m.col_asof(), value: (r) => r.asof_et ?? '' },
            { id: 'tfs', header: m.col_timeframe(), value: (r) => (r.timeframes ?? []).join(' '),
              cell: (r) => (
                <span className="flex flex-wrap gap-1">
                  {(r.timeframes ?? []).map((tf) => <Badge key={tf} tone="outline">{tf}</Badge>)}
                </span>
              ) },
            { id: 'list', header: m.col_list(), value: (r) => r.list_name ?? m.all_lists() },
            { id: 'kill', header: m.col_kill_pct(), numeric: true, noSearch: true,
              value: (r) => r.kill_pct, cell: (r) => fmt.number(r.kill_pct, 1) },
            { id: 'regime', header: m.col_regime(), value: (r) => r.regime_hint ?? '' },
          ]}
        />
      )}
    </QueryState>
  )
}
