import { useState } from 'react'
import { m } from '../../../paraglide/messages.js'
import { useAction } from '../../../services/api/action.ts'
import { domainConfig } from '../../../config/domain.ts'
import { ActionStatus } from '../../../components/ui/ActionStatus.tsx'
import { Card, CardContent, CardFooter, CardHeader } from '../../../components/ui/Card.tsx'
import { ChipGroup } from '../../../components/ui/ChoiceChips.tsx'
import { ConfirmAction } from '../../../components/ui/ConfirmAction.tsx'
import { inlineFieldClass } from '../../../components/ui/form.ts'
import { PlayIcon, RadarIcon, TrashIcon } from '../../../components/ui/icons.tsx'
import { deleteRoundAction, runRoundAction, useRoundStatus } from '../api.ts'
import { isRunning } from '../model.ts'

const { radarTimeframes } = domainConfig.domain

export function RunRound({ defaultOpen }: { defaultOpen?: boolean }) {
  const status = useRoundStatus()
  const run = useAction(runRoundAction,
    { success: (d) => m.radar_run_started({ status: d.status }) })
  const [tfs, setTfs] = useState<string[]>([...radarTimeframes])
  const [newRecord, setNewRecord] = useState(false)
  return (
    <Card testId="run-round">
      <CardHeader icon={RadarIcon} title={m.radar_run()} description={m.radar_run_hint()} />
      <CardContent className="space-y-4">
        <ChipGroup legend={m.field_timeframes()} options={radarTimeframes} value={tfs}
          onChange={setTfs} />
        <label className={inlineFieldClass}>
          <input type="checkbox" checked={newRecord}
            onChange={(e) => setNewRecord(e.target.checked)} />
          {m.radar_new_record()}
        </label>
      </CardContent>
      <CardFooter>
        <ConfirmAction
          tone="normal"
          icon={PlayIcon}
          label={m.radar_run()}
          title={m.radar_run()}
          details={newRecord ? m.radar_run_details_new({ tfs: tfs.join(', ') })
            : m.radar_run_details({ tfs: tfs.join(', ') })}
          confirmLabel={m.radar_run()}
          disabled={tfs.length === 0 || isRunning(status.data) || run.isPending}
          defaultOpen={defaultOpen}
          onConfirm={() => run.mutate({ timeframes: tfs, newRecord })}
        />
        <ActionStatus action={run} />
      </CardFooter>
    </Card>
  )
}

export function DeleteRound({ stamp, onDeleted, defaultOpen }: {
  stamp: string
  onDeleted?: () => void
  defaultOpen?: boolean
}) {
  const del = useAction(deleteRoundAction)
  return (
    <span className="inline-flex items-center gap-2" data-testid="delete-round">
      <ConfirmAction
        icon={TrashIcon}
        variant="outline"
        size="sm"
        label={m.radar_delete()}
        title={m.radar_delete()}
        details={m.radar_delete_details({ stamp })}
        confirmLabel={m.radar_delete_confirm({ stamp })}
        disabled={del.isPending}
        defaultOpen={defaultOpen}
        onConfirm={() => del.mutate(stamp, { onSuccess: onDeleted })}
      />
      <ActionStatus action={del} />
    </span>
  )
}
