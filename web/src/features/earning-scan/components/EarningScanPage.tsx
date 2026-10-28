import { m } from '../../../paraglide/messages.js'
import { serverText } from '../../../services/api/serverMessages.ts'
import { useFormat } from '../../../hooks/useFormat.ts'
import { DataTable } from '../../../components/ui/DataTable.tsx'
import { Disclosure } from '../../../components/ui/Disclosure.tsx'
import { Badge } from '../../../components/ui/Feedback.tsx'
import { PageHeader } from '../../../components/ui/PageHeader.tsx'
import { QueryState } from '../../../components/ui/QueryState.tsx'
import { useEarningHistory } from '../api.ts'
import { epsVerdict, latestQuarter } from '../model.ts'
import type { EarningRun, SymbolResult } from '../schemas.ts'
import { EarningScanForm } from './EarningScanForm.tsx'

const VERDICT_MARK = { 1: '▲', 0: '·', [-1]: '▼' } as const
const VERDICT_CLASS = { 1: 'text-up', 0: 'text-muted-foreground', [-1]: 'text-down' } as const

function RunTable({ run }: { run: EarningRun }) {
  const fmt = useFormat()
  return (
    <Disclosure testId="earning-run" summary={(
      <>
        <span className="font-medium">{fmt.dateTime(run.timestamp)}</span>
        <Badge tone="secondary">{m.earning_run_summary({ count: run.symbols.length })}</Badge>
      </>
    )}>
      <DataTable<SymbolResult>
        rows={run.results}
        rowKey={(r) => r.symbol}
        columns={[
          { id: 'symbol', header: m.col_symbol(), value: (r) => r.symbol,
            cell: (r) => <span className="font-semibold">{r.symbol}</span> },
          { id: 'provider', header: m.col_provider(), value: (r) => r.provider ?? '' },
          { id: 'period', header: m.col_period(), value: (r) => latestQuarter(r)?.period ?? '' },
          { id: 'eps', header: m.col_eps(), numeric: true, noSearch: true,
            value: (r) => epsVerdict(latestQuarter(r)),
            cell: (r) => {
              const q = latestQuarter(r)
              const v = epsVerdict(q)
              const text = `${fmt.number(q?.eps_actual)} / ${fmt.number(q?.eps_estimate)}`
              return <span className={VERDICT_CLASS[v]}>{VERDICT_MARK[v]} {text}</span>
            } },
          { id: 'next', header: m.col_next_earnings(), value: (r) => r.next_earnings_date ?? '' },
          { id: 'error', header: m.col_note(),
            value: (r) => serverText({ code: r.error_code, text: r.error }) },
        ]}
      />
    </Disclosure>
  )
}

export function EarningScanPage() {
  const query = useEarningHistory()
  return (
    <section className="space-y-6">
      <PageHeader description={m.page_desc_earning_scan()} />
      <EarningScanForm />
      <h2 className="text-sm font-semibold text-muted-foreground">{m.runs_title()}</h2>
      <QueryState query={query} isEmpty={(d) => d.length === 0}>
        {(runs) => (
          <div className="space-y-3">{runs.map((r) => <RunTable key={r.id} run={r} />)}</div>
        )}
      </QueryState>
    </section>
  )
}
