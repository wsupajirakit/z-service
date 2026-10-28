import { useState } from 'react'
import { m } from '../../../paraglide/messages.js'
import { useFormat } from '../../../hooks/useFormat.ts'
import { Card, CardContent, CardHeader, StatCard, StatGrid } from '../../../components/ui/Card.tsx'
import { DataTable } from '../../../components/ui/DataTable.tsx'
import { Badge, EmptyState } from '../../../components/ui/Feedback.tsx'
import { BriefcaseIcon, ChartIcon, CoinsIcon } from '../../../components/ui/icons.tsx'
import { PageHeader } from '../../../components/ui/PageHeader.tsx'
import { QueryState } from '../../../components/ui/QueryState.tsx'
import { Tabs } from '../../../components/ui/Tabs.tsx'
import { usePortfolio } from '../api.ts'
import { summarize, type PortSummary } from '../model.ts'
import { AddTradeDialog, RemoveSymbolButton, RenamePortDialog } from './PortEditor.tsx'
import type { Position, Trade } from '../schemas.ts'

function PositionsTable({ port }: { port: PortSummary }) {
  const fmt = useFormat()
  return (
    <DataTable<Position>
      rows={port.positions}
      rowKey={(r) => r.symbol}
      columns={[
        { id: 'symbol', header: m.col_symbol(), value: (r) => r.symbol,
          cell: (r) => <span className="font-semibold">{r.symbol}</span> },
        { id: 'qty', header: m.col_quantity(), numeric: true, noSearch: true,
          value: (r) => r.total_quantity, cell: (r) => fmt.number(r.total_quantity) },
        { id: 'avg', header: m.col_avg_price(), numeric: true, noSearch: true,
          value: (r) => r.avg_price, cell: (r) => fmt.number(r.avg_price) },
        { id: 'cost', header: m.pf_col_cost(), numeric: true, noSearch: true,
          value: (r) => r.total_quantity * r.avg_price,
          cell: (r) => fmt.number(r.total_quantity * r.avg_price) },
        { id: 'actions', header: '', numeric: true,
          cell: (r) => <RemoveSymbolButton port={port.name} symbol={r.symbol} /> },
      ]}
    />
  )
}

function TradesTable({ port }: { port: PortSummary }) {
  const fmt = useFormat()
  const open = new Set(port.positions.map((p) => p.symbol))
  return (
    <DataTable<Trade>
      rows={port.trades}
      rowKey={(r, i) => `${r.timestamp ?? ''}-${r.symbol}-${i}`}
      columns={[
        { id: 'time', header: m.col_time(), value: (r) => r.timestamp, noSearch: true,
          cell: (r) => fmt.dateTime(r.timestamp) },
        { id: 'symbol', header: m.col_symbol(), value: (r) => r.symbol },
        { id: 'action', header: m.col_action(), value: (r) => r.action,
          cell: (r) => <Badge tone={r.action === 'sell' ? 'destructive' : 'success'}>
            {r.action === 'sell' ? m.trade_sell() : m.trade_buy()}</Badge> },
        { id: 'qty', header: m.col_quantity(), numeric: true, noSearch: true,
          value: (r) => r.quantity, cell: (r) => fmt.number(r.quantity) },
        { id: 'price', header: m.col_price(), numeric: true, noSearch: true,
          value: (r) => r.buy_price, cell: (r) => fmt.number(r.buy_price) },
        // A symbol with trades but no open position can only be removed from here.
        { id: 'actions', header: '', numeric: true, cell: (r) => (open.has(r.symbol) ? null
          : <RemoveSymbolButton port={port.name} symbol={r.symbol} />) },
      ]}
    />
  )
}

function PortCard({ port }: { port: PortSummary }) {
  const fmt = useFormat()
  const [tab, setTab] = useState<'positions' | 'trades'>('positions')
  return (
    <Card testId="port">
      <CardHeader
        icon={BriefcaseIcon}
        title={port.name}
        description={m.portfolio_cost({ cost: fmt.number(port.cost) })}
        actions={<RenamePortDialog key={port.name} port={port.name} />}
      />
      <CardContent className="space-y-4">
        <Tabs
          label={port.name}
          value={tab}
          onChange={setTab}
          items={[
            { value: 'positions', label: m.pf_tab_positions({ count: port.positions.length }) },
            { value: 'trades', label: m.portfolio_trades({ count: port.trades.length }) },
          ]}
        />
        {tab === 'positions' ? <PositionsTable port={port} /> : <TradesTable port={port} />}
      </CardContent>
    </Card>
  )
}

function Summary({ ports }: { ports: PortSummary[] }) {
  const fmt = useFormat()
  const positions = ports.reduce((n, p) => n + p.positions.length, 0)
  const cost = ports.reduce((n, p) => n + p.cost, 0)
  return (
    <StatGrid>
      <StatCard label={m.pf_stat_ports()} value={fmt.number(ports.length, 0)}
        icon={BriefcaseIcon} />
      <StatCard label={m.pf_stat_positions()} value={fmt.number(positions, 0)} icon={ChartIcon} />
      <StatCard label={m.pf_stat_cost()} value={fmt.number(cost)} icon={CoinsIcon} />
    </StatGrid>
  )
}

export function PortfolioPage() {
  const query = usePortfolio()
  const names = Object.keys(query.data ?? {}).sort()
  return (
    <section className="space-y-6">
      <PageHeader description={m.page_desc_portfolio()}>
        {/* Remount when the names arrive so the portfolio field starts on the first one. */}
        <AddTradeDialog key={names.join('\n')} ports={names} />
      </PageHeader>
      <QueryState query={query}>
        {(data) => {
          const ports = summarize(data)
          if (ports.length === 0) return <EmptyState />
          return (
            <>
              <Summary ports={ports} />
              {ports.map((p) => <PortCard key={p.name} port={p} />)}
            </>
          )
        }}
      </QueryState>
    </section>
  )
}
