import { useState } from 'react'
import { m } from '../../../paraglide/messages.js'
import { useWatchlist } from '../../../services/api/lists.ts'
import { domainConfig } from '../../../config/domain.ts'
import { Card, CardContent, CardHeader } from '../../../components/ui/Card.tsx'
import { Alert } from '../../../components/ui/Feedback.tsx'
import { button, fieldClass, formRowClass, selectClass } from '../../../components/ui/form.ts'
import { DownloadIcon } from '../../../components/ui/icons.tsx'
import { PageHeader } from '../../../components/ui/PageHeader.tsx'
import { QueryState } from '../../../components/ui/QueryState.tsx'
import { exportLinks, useExportCheck } from '../api.ts'

const linkLabel = (id: string) => ({
  zip: m.export_zip(), part1: m.export_part({ part: 1 }), part2: m.export_part({ part: 2 }),
  all: m.export_all(), formula: m.export_formula(), news: m.export_news(),
})[id] ?? id

export function ExportCheckView({ interval, list }: { interval: string; list: string }) {
  const check = useExportCheck(interval, list)
  return (
    <QueryState query={check}>
      {(c) => (
        <div data-testid="export-check">
          <Alert tone={c.missing_count > 0 ? 'warning' : 'success'}
            title={m.export_check({ available: c.available_count, total: c.total_in_list,
              missing: c.missing_count })}>
            {c.missing_symbols.length > 0 && c.missing_symbols.join(', ')}
          </Alert>
        </div>
      )}
    </QueryState>
  )
}

export function ExportPage() {
  const lists = Object.keys(useWatchlist().data ?? {}).sort()
  const [interval, setTf] = useState('1d')
  const [list, setList] = useState<string>(domainConfig.domain.allSymbolsList)
  return (
    <section className="space-y-6">
      <PageHeader description={m.page_desc_export()} />
      <Card>
        <CardHeader icon={DownloadIcon} title={m.export_card_title()} />
        <CardContent className="space-y-5">
          <div className={formRowClass}>
            <label className={fieldClass}>{m.field_interval()}
              <select className={selectClass} value={interval}
                onChange={(e) => setTf(e.target.value)}>
                {domainConfig.domain.fetchTimeframes.map((tf) => <option key={tf}>{tf}</option>)}
              </select>
            </label>
            <label className={fieldClass}>{m.field_list()}
              <select className={selectClass} value={list}
                onChange={(e) => setList(e.target.value)}>
                <option value={domainConfig.domain.allSymbolsList}>{m.export_all_symbols()}</option>
                {lists.map((l) => <option key={l} value={l}>{l}</option>)}
              </select>
            </label>
          </div>
          <ExportCheckView interval={interval} list={list} />
          <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3" data-testid="export-links">
            {exportLinks(interval, list).map((l) => (
              <li key={l.id}>
                <a className={button('outline', 'md', 'block')} href={l.href}
                  download={l.file}>
                  <DownloadIcon />
                  {linkLabel(l.id)}
                </a>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </section>
  )
}
