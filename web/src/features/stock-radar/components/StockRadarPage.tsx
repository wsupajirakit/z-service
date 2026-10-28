import { m } from '../../../paraglide/messages.js'
import { useFormat } from '../../../hooks/useFormat.ts'
import { MarkdownText } from '../../../components/MarkdownText.tsx'
import { Disclosure } from '../../../components/ui/Disclosure.tsx'
import { EmptyState } from '../../../components/ui/Feedback.tsx'
import { PageHeader } from '../../../components/ui/PageHeader.tsx'
import { QueryState } from '../../../components/ui/QueryState.tsx'
import { useRadarHistory } from '../api.ts'
import { runSummary } from '../model.ts'
import type { RadarRun } from '../schemas.ts'
import { ScanForm } from './ScanForm.tsx'

function RunCard({ run }: { run: RadarRun }) {
  const fmt = useFormat()
  const summary = runSummary(run)
  return (
    <Disclosure testId="radar-run" summary={(
      <>
        <span className="font-medium">{fmt.dateTime(run.timestamp)}</span>
        <span className="text-muted-foreground">
          {m.stock_radar_summary({
            symbols: summary.symbols,
            timeframes: run.timeframes.join(' '),
            formulas: summary.formulas.join(', '),
          })}
        </span>
      </>
    )}>
      <p className="font-mono text-xs text-muted-foreground">{run.symbols.join(' ')}</p>
      {run.result_markdown ? <MarkdownText source={run.result_markdown} /> : <EmptyState />}
    </Disclosure>
  )
}

export function StockRadarPage() {
  const query = useRadarHistory()
  return (
    <section className="space-y-6">
      <PageHeader description={m.page_desc_stock_radar()} />
      <ScanForm />
      <h2 className="text-sm font-semibold text-muted-foreground">{m.runs_title()}</h2>
      <QueryState query={query} isEmpty={(d) => d.length === 0}>
        {(runs) => (
          <div className="space-y-3">{runs.map((r) => <RunCard key={r.id} run={r} />)}</div>
        )}
      </QueryState>
    </section>
  )
}
