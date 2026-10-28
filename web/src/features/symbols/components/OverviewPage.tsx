import { m } from '../../../paraglide/messages.js'
import { useVersion } from '../../../services/api/common.ts'
import { useFormat } from '../../../hooks/useFormat.ts'
import { Card, CardContent, CardHeader, StatCard, StatGrid } from '../../../components/ui/Card.tsx'
import { DataTable } from '../../../components/ui/DataTable.tsx'
import { Alert, Badge } from '../../../components/ui/Feedback.tsx'
import { ActivityIcon, ChartIcon, InfoIcon, ListIcon } from '../../../components/ui/icons.tsx'
import { PageHeader } from '../../../components/ui/PageHeader.tsx'
import { QueryState } from '../../../components/ui/QueryState.tsx'
import { useSymbols } from '../api.ts'
import { exchangeCounts, type ExchangeCount } from '../model.ts'
import type { SymbolsInfo } from '../schemas.ts'

function VersionPanel() {
  const query = useVersion()
  const fmt = useFormat()
  return (
    <Card>
      <CardHeader title={m.version_label()} icon={InfoIcon} />
      <CardContent>
        <QueryState query={query}>
          {(v) => (
            <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm"
              data-testid="version-panel">
              <dt className="text-muted-foreground">{m.version_label()}</dt>
              <dd className="font-mono">{v.version} ({v.commit ?? ''})</dd>
              <dt className="text-muted-foreground">{m.version_built()}</dt>
              <dd>{fmt.dateTime(v.build_time)}</dd>
              <dt className="text-muted-foreground">{m.version_job()}</dt>
              <dd>{m.version_job_value({
                phase: v.job_phase ?? '-',
                round: v.job_round ?? 0,
                total: v.job_total ?? 0,
              })}</dd>
              <dt className="text-muted-foreground">{m.version_autostart()}</dt>
              <dd>
                <Badge tone={v.autostart ? 'success' : 'secondary'}>
                  {v.autostart ? m.yes() : m.no()}
                </Badge>
              </dd>
            </dl>
          )}
        </QueryState>
      </CardContent>
    </Card>
  )
}

function SymbolStats({ info }: { info: SymbolsInfo }) {
  const fmt = useFormat()
  const counts = exchangeCounts(info)
  return (
    <StatGrid>
      <StatCard label={m.col_symbols()} value={fmt.number(info.count, 0)} icon={ListIcon}
        testId="symbol-count"
        hint={m.symbols_total({
          count: info.count,
          build: info.sources?.build ?? 0,
          extra: info.sources?.db_extra ?? 0,
        })} />
      <StatCard label={m.overview_exchanges()} value={fmt.number(counts.length, 0)}
        icon={ChartIcon} hint={counts[0] ? m.overview_top_exchange({
          exchange: counts[0].exchange, count: counts[0].count }) : undefined} />
      <StatCard label={m.overview_missing()} value={fmt.number(info.missing_exchange.length, 0)}
        icon={ActivityIcon} />
    </StatGrid>
  )
}

export function OverviewPage() {
  const query = useSymbols()
  const fmt = useFormat()
  return (
    <section className="space-y-6">
      <PageHeader description={m.page_desc_home()} />
      <QueryState query={query}>
        {(info) => (
          <>
            <SymbolStats info={info} />
            {info.missing_exchange.length > 0 && (
              <Alert tone="warning" title={m.overview_missing()}>
                {m.symbols_missing_exchange({ symbols: info.missing_exchange.join(' ') })}
              </Alert>
            )}
            <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
              <Card>
                <CardHeader title={m.overview_by_exchange()} icon={ChartIcon} />
                <CardContent>
                  <DataTable<ExchangeCount>
                    rows={exchangeCounts(info)}
                    rowKey={(r) => r.exchange}
                    initialSort={{ id: 'n', desc: true }}
                    columns={[
                      { id: 'ex', header: m.col_exchange(), value: (r) => r.exchange },
                      {
                        id: 'n',
                        header: m.col_symbols(),
                        numeric: true,
                        value: (r) => r.count,
                        cell: (r) => fmt.number(r.count, 0),
                      },
                    ]}
                  />
                </CardContent>
              </Card>
              <VersionPanel />
            </div>
          </>
        )}
      </QueryState>
    </section>
  )
}
