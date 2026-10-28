import { useState } from 'react'
import { m } from '../../../paraglide/messages.js'
import { useAction } from '../../../services/api/action.ts'
import { useSymbols } from '../../../services/api/lists.ts'
import { domainConfig } from '../../../config/domain.ts'
import { toTargets } from '../../../utils/symbols.ts'
import { intInRange } from '../../../utils/validate.ts'
import { ActionStatus } from '../../../components/ui/ActionStatus.tsx'
import { Card, CardContent, CardFooter, CardHeader } from '../../../components/ui/Card.tsx'
import { ChipGroup } from '../../../components/ui/ChoiceChips.tsx'
import { ConfirmAction } from '../../../components/ui/ConfirmAction.tsx'
import { fieldClass, formRowClass, inlineFieldClass, inputClass } from
  '../../../components/ui/form.ts'
import { DownloadIcon, PlayIcon } from '../../../components/ui/icons.tsx'
import { SymbolPicker } from '../../../components/ui/SymbolPicker.tsx'
import { customRunAction } from '../api.ts'

const { fetchTimeframes, defaultRows } = domainConfig.domain
const { rows: rowLimit } = domainConfig.limits

export function CustomRun({ busy }: { busy: boolean }) {
  const run = useAction(customRunAction)
  const all = useSymbols().data?.symbols ?? []
  const [tfs, setTfs] = useState<string[]>(['1d'])
  const [picked, setPicked] = useState<string[]>([])
  const [rows, setRows] = useState(String(defaultRows))
  const [extended, setExtended] = useState(false)
  const { targets } = toTargets(picked, all)
  const rowsOk = intInRange(rows, rowLimit.min, rowLimit.max)
  return (
    <Card testId="custom-run">
      <CardHeader icon={DownloadIcon} title={m.custom_title()}
        description={m.custom_description()} />
      <CardContent className="space-y-4">
        <ChipGroup legend={m.field_timeframes()} options={fetchTimeframes} value={tfs}
          onChange={setTfs} />
        <SymbolPicker value={picked} onChange={setPicked} />
        <div className={formRowClass}>
          <label className={fieldClass}>
            {m.field_rows()}
            <input className={`${inputClass} w-28`} type="number" value={rows}
              onChange={(e) => setRows(e.target.value)} />
          </label>
          <label className={`${inlineFieldClass} pb-2`}>
            <input type="checkbox" checked={extended}
              onChange={(e) => setExtended(e.target.checked)} />
            {m.field_extended()}
          </label>
        </div>
      </CardContent>
      <CardFooter>
        <ConfirmAction
          tone="normal"
          icon={PlayIcon}
          label={m.custom_start()}
          title={m.custom_start()}
          details={m.custom_details({ count: targets.length, tfs: tfs.join(', '),
            rows: rowsOk ?? 0 })}
          confirmLabel={m.auto_start_confirm()}
          disabled={busy || targets.length === 0 || tfs.length === 0 || rowsOk === null}
          onConfirm={() => rowsOk !== null
            && run.mutate({ timeframes: tfs, targets, rows: rowsOk, extended })}
        />
        <ActionStatus action={run} />
      </CardFooter>
    </Card>
  )
}
