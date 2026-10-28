import { useState } from 'react'
import { m } from '../../../paraglide/messages.js'
import { useAction } from '../../../services/api/action.ts'
import { replyText, type StatusReply } from '../../../services/api/common.ts'
import { domainConfig } from '../../../config/domain.ts'
import { intInRange } from '../../../utils/validate.ts'
import { ActionStatus } from '../../../components/ui/ActionStatus.tsx'
import { Card, CardContent, CardHeader } from '../../../components/ui/Card.tsx'
import { ConfirmAction } from '../../../components/ui/ConfirmAction.tsx'
import { fieldClass, formRowClass, inputClass } from '../../../components/ui/form.ts'
import { TrashIcon } from '../../../components/ui/icons.tsx'
import { cleanupAction, clearAllAction } from '../maintenance.ts'

const { cleanupHours } = domainConfig.limits

export function HistoryMaintenance({ defaultOpen }: { defaultOpen?: 'cleanup' | 'clear' }) {
  const notice = { success: (d: StatusReply) => replyText(d, m.action_done()) }
  const cleanup = useAction(cleanupAction, notice)
  const clear = useAction(clearAllAction, notice)
  const [hours, setHours] = useState('2')
  const h = intInRange(hours, cleanupHours.min, cleanupHours.max)
  return (
    <Card testId="history-maintenance">
      <CardHeader icon={TrashIcon} title={m.history_maintenance()}
        description={m.history_maintenance_hint()} />
      <CardContent className="space-y-3">
        <div className={formRowClass}>
          <label className={fieldClass}>
            {m.history_hours({ min: cleanupHours.min, max: cleanupHours.max })}
            <input className={`${inputClass} w-32`} type="number" min={cleanupHours.min}
              max={cleanupHours.max} value={hours} onChange={(e) => setHours(e.target.value)} />
          </label>
          <ConfirmAction
            variant="outline"
            label={m.history_cleanup()}
            title={m.history_cleanup()}
            details={m.history_cleanup_details({ hours: h ?? 0 })}
            confirmLabel={m.history_cleanup()}
            disabled={h === null || cleanup.isPending}
            defaultOpen={defaultOpen === 'cleanup'}
            onConfirm={() => h !== null && cleanup.mutate(h)}
          />
          <ConfirmAction
            label={m.history_clear()}
            title={m.history_clear()}
            details={m.history_clear_details()}
            confirmLabel={m.history_clear_confirm()}
            disabled={clear.isPending}
            defaultOpen={defaultOpen === 'clear'}
            onConfirm={() => clear.mutate()}
          />
        </div>
        <ActionStatus action={cleanup} />
        <ActionStatus action={clear} />
      </CardContent>
    </Card>
  )
}
