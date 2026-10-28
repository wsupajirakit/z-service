import { useState } from 'react'
import { m } from '../../../paraglide/messages.js'
import { useAction } from '../../../services/api/action.ts'
import { useSymbols } from '../../../services/api/lists.ts'
import { domainConfig } from '../../../config/domain.ts'
import { MarkdownText } from '../../../components/MarkdownText.tsx'
import { toTargets } from '../../../utils/symbols.ts'
import { ActionStatus } from '../../../components/ui/ActionStatus.tsx'
import { Card, CardContent, CardFooter, CardHeader } from '../../../components/ui/Card.tsx'
import { ChipGroup } from '../../../components/ui/ChoiceChips.tsx'
import { ConfirmAction } from '../../../components/ui/ConfirmAction.tsx'
import { fieldClass, formRowClass, inlineFieldClass, selectClass } from
  '../../../components/ui/form.ts'
import { PlayIcon, ScanIcon } from '../../../components/ui/icons.tsx'
import { SymbolPicker } from '../../../components/ui/SymbolPicker.tsx'
import { scanAction } from '../api.ts'

const { stockRadarFormulas, radarTimeframes, stockRadarModes } = domainConfig.domain

export function ScanForm({ defaultOpen }: { defaultOpen?: boolean }) {
  const scan = useAction(scanAction)
  const all = useSymbols().data?.symbols ?? []
  const [picked, setPicked] = useState<string[]>([])
  const [formulas, setFormulas] = useState<string[]>(['UIPT'])
  const [tfs, setTfs] = useState<string[]>(['1D'])
  const [mode, setMode] = useState<string>(stockRadarModes[0])
  const [extended, setExtended] = useState(false)
  const { targets } = toTargets(picked, all)
  const ready = targets.length > 0 && formulas.length > 0 && tfs.length > 0
  return (
    <Card testId="radar-scan">
      <CardHeader icon={ScanIcon} title={m.scan_title()} description={m.scan_description()} />
      <CardContent className="space-y-4">
        <SymbolPicker value={picked} onChange={setPicked} />
        <div className="grid gap-4 sm:grid-cols-2">
          <ChipGroup legend={m.scan_formulas()} options={stockRadarFormulas} value={formulas}
            onChange={setFormulas} />
          <ChipGroup legend={m.field_timeframes()} options={radarTimeframes} value={tfs}
            onChange={setTfs} />
        </div>
        <div className={formRowClass}>
          <label className={fieldClass}>{m.scan_mode()}
            <select className={selectClass} value={mode} onChange={(e) => setMode(e.target.value)}>
              {stockRadarModes.map((x) => <option key={x} value={x}>
                {x === 'ai' ? m.scan_mode_ai() : m.scan_mode_logic()}</option>)}
            </select>
          </label>
          <label className={`${inlineFieldClass} pb-2`}>
            <input type="checkbox" checked={extended}
              onChange={(e) => setExtended(e.target.checked)} />
            {m.field_extended()}
          </label>
        </div>
        {scan.status === 'success' && (
          <div className="rounded-lg border bg-muted/30 p-4">
            <MarkdownText source={scan.data.analysis} />
          </div>
        )}
      </CardContent>
      <CardFooter>
        <ConfirmAction
          tone={mode === 'ai' ? 'cost' : 'normal'}
          variant="default"
          icon={PlayIcon}
          label={m.scan_start()}
          title={m.scan_start()}
          details={m.scan_details({ count: targets.length, tfs: tfs.join(', '),
            formulas: formulas.join(', '), calls: targets.length * tfs.length })}
          confirmLabel={m.scan_start()}
          disabled={!ready || scan.isPending}
          defaultOpen={defaultOpen}
          onConfirm={() => scan.mutate({ targets, formulas, timeframes: tfs, extended, mode })}
        />
        <ActionStatus action={scan} />
      </CardFooter>
    </Card>
  )
}
