import { useMemo, useState } from 'react'
import { m } from '../../../paraglide/messages.js'
import { useAction } from '../../../services/api/action.ts'
import { useSymbols } from '../../../services/api/lists.ts'
import { toCandles } from '../../../components/chart/candles.ts'
import { ChartPanel } from '../../../components/chart/ChartPanel.tsx'
import { domainConfig } from '../../../config/domain.ts'
import { useFormat } from '../../../hooks/useFormat.ts'
import { cleanExchange, cleanSymbol, intInRange } from '../../../utils/validate.ts'
import { ActionStatus } from '../../../components/ui/ActionStatus.tsx'
import { Card, CardContent, CardHeader } from '../../../components/ui/Card.tsx'
import { DataTable } from '../../../components/ui/DataTable.tsx'
import { button, fieldClass, formRowClass, inlineFieldClass, inputClass, selectClass } from
  '../../../components/ui/form.ts'
import { SearchIcon } from '../../../components/ui/icons.tsx'
import { fetchDataAction } from '../api.ts'
import { barColumns } from '../model.ts'
import type { Bars } from '../schemas.ts'

function BarsView({ bars }: { bars: Bars }) {
  const fmt = useFormat()
  const candles = useMemo(() => toCandles(bars), [bars])
  const columns = barColumns(bars).map((id) => ({
    id,
    header: id,
    numeric: id !== 'datetime' && id !== 'symbol',
    noSearch: id !== 'datetime',
    value: (r: Record<string, unknown>) => {
      const v = r[id]
      return typeof v === 'number' || typeof v === 'string' ? v : null
    },
    cell: (r: Record<string, unknown>) =>
      typeof r[id] === 'number' ? fmt.number(r[id]) : String(r[id] ?? ''),
  }))
  return (
    <div className="space-y-4">
      {candles.length > 0 && <ChartPanel title={m.chart_title()} candles={candles} />}
      <DataTable rows={[...bars].reverse()} columns={columns}
        rowKey={(r, i) => `${String(r.datetime ?? '')}-${i}`} testId="bars" />
    </div>
  )
}

export function SingleFetch() {
  const fetchData = useAction(fetchDataAction)
  const all = useSymbols().data?.symbols ?? []
  const [form, setForm] = useState({ symbol: '', exchange: '', interval: '1d',
    rows: String(domainConfig.domain.dataRows), extended: false })
  const symbol = cleanSymbol(form.symbol)
  const known = all.find((s) => s.symbol === symbol)?.exchange ?? ''
  const exchange = cleanExchange(form.exchange || known)
  const rows = intInRange(form.rows, domainConfig.limits.rows.min, domainConfig.limits.rows.max)
  const ok = symbol && exchange && rows !== null
  return (
    <Card testId="single-fetch">
      <CardHeader icon={SearchIcon} title={m.fetch_title()} description={m.fetch_description()} />
      <CardContent className="space-y-4">
        <form className={formRowClass} onSubmit={(e) => {
          e.preventDefault()
          if (ok) fetchData.mutate({ symbol, exchange, interval: form.interval, rows,
            extended: form.extended })
        }}>
          <label className={fieldClass}>{m.field_symbol()}
            <input className={`${inputClass} w-36`} list="fetch-symbols" value={form.symbol}
              onChange={(e) => setForm({ ...form, symbol: e.target.value })} />
          </label>
          <datalist id="fetch-symbols">
            {all.map((s) => <option key={s.symbol} value={s.symbol}>{s.name}</option>)}
          </datalist>
          <label className={fieldClass}>{m.field_exchange()}
            <input className={`${inputClass} w-32`} value={form.exchange} placeholder={known}
              onChange={(e) => setForm({ ...form, exchange: e.target.value })} />
          </label>
          <label className={fieldClass}>{m.field_interval()}
            <select className={selectClass} value={form.interval}
              onChange={(e) => setForm({ ...form, interval: e.target.value })}>
              {domainConfig.domain.fetchTimeframes.map((tf) => <option key={tf}>{tf}</option>)}
            </select>
          </label>
          <label className={fieldClass}>{m.field_rows()}
            <input className={`${inputClass} w-24`} type="number" value={form.rows}
              onChange={(e) => setForm({ ...form, rows: e.target.value })} />
          </label>
          <label className={`${inlineFieldClass} pb-2`}>
            <input type="checkbox" checked={form.extended}
              onChange={(e) => setForm({ ...form, extended: e.target.checked })} />
            {m.field_extended()}
          </label>
          <button type="submit" className={button('default')}
            disabled={!ok || fetchData.isPending}>
            {m.fetch_run()}
          </button>
        </form>
        {fetchData.status === 'success' ? <BarsView bars={fetchData.data} />
          : <ActionStatus action={fetchData} />}
      </CardContent>
    </Card>
  )
}
