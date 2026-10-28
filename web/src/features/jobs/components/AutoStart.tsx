import { useState } from 'react'
import { m } from '../../../paraglide/messages.js'
import { useAction } from '../../../services/api/action.ts'
import { useSymbols } from '../../../services/api/lists.ts'
import { domainConfig } from '../../../config/domain.ts'
import { toTargets } from '../../../utils/symbols.ts'
import { intInRange } from '../../../utils/validate.ts'
import { ActionStatus } from '../../../components/ui/ActionStatus.tsx'
import { Card, CardContent, CardFooter, CardHeader } from '../../../components/ui/Card.tsx'
import { ConfirmAction } from '../../../components/ui/ConfirmAction.tsx'
import { Alert } from '../../../components/ui/Feedback.tsx'
import { fieldClass, formRowClass, inlineFieldClass, inputClass } from
  '../../../components/ui/form.ts'
import { PlayIcon, RefreshIcon } from '../../../components/ui/icons.tsx'
import { SymbolPicker } from '../../../components/ui/SymbolPicker.tsx'
import { startAllAction, startAutoAction } from '../api.ts'

const { rows: rowLimit } = domainConfig.limits

export function AutoStart({ busy }: { busy: boolean }) {
  const startAll = useAction(startAllAction)
  const start = useAction(startAutoAction)
  const all = useSymbols().data?.symbols ?? []
  const [picked, setPicked] = useState<string[]>([])
  const [rows, setRows] = useState(String(domainConfig.domain.defaultRows))
  const [legacy, setLegacy] = useState(false)
  const { targets, missing } = toTargets(picked, all)
  const rowsOk = intInRange(rows, rowLimit.min, rowLimit.max)
  return (
    <Card testId="auto-start">
      <CardHeader icon={RefreshIcon} title={m.auto_title()} description={m.auto_description()}
        actions={(
          <ConfirmAction
            tone="normal"
            variant="secondary"
            size="sm"
            label={m.auto_start_all()}
            title={m.auto_start_all()}
            details={m.auto_start_all_details()}
            confirmLabel={m.auto_start_confirm()}
            disabled={busy || startAll.isPending}
            onConfirm={() => startAll.mutate()}
          />
        )} />
      <CardContent className="space-y-4">
        <ActionStatus action={startAll} />
        <SymbolPicker value={picked} onChange={setPicked} />
        <div className={formRowClass}>
          <label className={fieldClass}>
            {m.field_rows()}
            <input className={`${inputClass} w-28`} type="number" value={rows}
              onChange={(e) => setRows(e.target.value)} />
          </label>
          <label className={`${inlineFieldClass} pb-2`}>
            <input type="checkbox" checked={legacy}
              onChange={(e) => setLegacy(e.target.checked)} />
            {m.auto_force_all_tf()}
          </label>
        </div>
        {missing.length > 0 && (
          <Alert tone="warning">{m.auto_missing_exchange({ list: missing.join(', ') })}</Alert>
        )}
      </CardContent>
      <CardFooter>
        <ConfirmAction
          tone="normal"
          icon={PlayIcon}
          label={m.auto_start_selected()}
          title={m.auto_start_selected()}
          details={legacy
            ? m.auto_start_details_legacy({ count: targets.length, rows: rowsOk ?? 0 })
            : m.auto_start_details_default({ count: targets.length, rows: rowsOk ?? 0 })}
          confirmLabel={m.auto_start_confirm()}
          disabled={busy || targets.length === 0 || rowsOk === null || start.isPending}
          onConfirm={() => rowsOk !== null
            && start.mutate({ targets, rows: rowsOk, forceAllTf: legacy })}
        />
        <ActionStatus action={start} />
      </CardFooter>
    </Card>
  )
}
