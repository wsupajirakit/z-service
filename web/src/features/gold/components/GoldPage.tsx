import { useState } from 'react'
import { m } from '../../../paraglide/messages.js'
import { useAction } from '../../../services/api/action.ts'
import { useFormat } from '../../../hooks/useFormat.ts'
import { MarkdownText } from '../../../components/MarkdownText.tsx'
import { ActionStatus } from '../../../components/ui/ActionStatus.tsx'
import { Card, CardContent, CardFooter, CardHeader, StatCard } from
  '../../../components/ui/Card.tsx'
import { ConfirmAction } from '../../../components/ui/ConfirmAction.tsx'
import { button, fieldClass, formRowClass, selectClass, selectSmClass } from
  '../../../components/ui/form.ts'
import { CoinsIcon, DownloadIcon, RefreshIcon, ScanIcon } from '../../../components/ui/icons.tsx'
import { PageHeader } from '../../../components/ui/PageHeader.tsx'
import {
  analyzeAction, goldExportHref, useGoldConfig, useGoldModels, useGoldModes, useGoldPrice,
} from '../api.ts'
import { GoldJobPanel } from './GoldJobPanel.tsx'

function GoldExports() {
  const modes = useGoldModes().data
  const [exchange, setExchange] = useState('')
  const ex = exchange || modes?.exchanges[0] || ''
  if (!modes) return null
  return (
    <Card testId="gold-exports">
      <CardHeader icon={DownloadIcon} title={m.gold_export_title()}
        actions={(
          <select className={selectSmClass} aria-label={m.gold_source()} value={ex}
            onChange={(e) => setExchange(e.target.value)}>
            {modes.exchanges.map((x) => <option key={x}>{x}</option>)}
          </select>
        )} />
      <CardContent>
        <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {modes.modes.map((md) => (
            <li key={md.mode}>
              <a className={button('outline', 'md', 'block')}
                href={goldExportHref(md.mode, ex)} download={`gold_${md.mode}.zip`}>
                <DownloadIcon />
                {`${md.mode} ${md.horizon ?? ''}`}
              </a>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}

export function GoldPage() {
  const fmt = useFormat()
  const config = useGoldConfig().data
  const models = useGoldModels().data
  const [exchange, setExchange] = useState('')
  const [model, setModel] = useState('')
  const run = { exchange: exchange || config?.sources[0]?.exchange || '',
    model: model || models?.default || config?.default_model || '' }
  const price = useGoldPrice(run.exchange)
  const analyze = useAction(analyzeAction)
  return (
    <section className="space-y-6">
      <PageHeader description={m.page_desc_gold()} />
      <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
        <StatCard label={m.gold_price_label()} icon={CoinsIcon} testId="gold-price"
          value={price.data ? fmt.number(price.data.price ?? NaN) : '—'} hint={run.exchange} />
        <Card>
          <CardHeader icon={ScanIcon} title={m.gold_analyze()} />
          <CardContent className={formRowClass}>
            <label className={fieldClass}>{m.gold_source()}
              <select className={selectClass} value={run.exchange}
                onChange={(e) => setExchange(e.target.value)}>
                {config?.sources.map((s) => <option key={s.exchange} value={s.exchange}>
                  {s.label}</option>)}
              </select>
            </label>
            <label className={fieldClass}>{m.gold_model()}
              <select className={selectClass} value={run.model}
                onChange={(e) => setModel(e.target.value)}>
                {(models?.models ?? []).map((x) => <option key={x.name} value={x.name}>
                  {x.displayName ?? x.name}</option>)}
              </select>
            </label>
            <button type="button" className={button('outline')} disabled={!run.exchange}
              onClick={() => void price.refetch()}>
              <RefreshIcon />
              {m.gold_price_refresh()}
            </button>
          </CardContent>
          <CardFooter>
            <ConfirmAction tone="cost" variant="default" icon={ScanIcon} label={m.gold_analyze()}
              title={m.gold_analyze()}
              details={m.gold_analyze_details({ exchange: run.exchange, model: run.model })}
              confirmLabel={m.gold_analyze()} disabled={!run.model || analyze.isPending}
              onConfirm={() => analyze.mutate(run)} />
            <ActionStatus action={analyze} />
          </CardFooter>
        </Card>
      </div>
      {analyze.status === 'success' && (
        <Card><CardContent className="pt-5"><MarkdownText source={analyze.data.analysis} />
        </CardContent></Card>
      )}
      <GoldJobPanel run={run} />
      <GoldExports />
    </section>
  )
}
