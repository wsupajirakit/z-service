import { m } from '../../../paraglide/messages.js'
import { useAction } from '../../../services/api/action.ts'
import { codeMessage } from '../../../services/api/errorMessages.ts'
import { enumLabel } from '../../../i18n/enums.ts'
import { useFormat } from '../../../hooks/useFormat.ts'
import { ActionStatus } from '../../../components/ui/ActionStatus.tsx'
import { Card, CardContent, CardHeader } from '../../../components/ui/Card.tsx'
import { ConfirmAction } from '../../../components/ui/ConfirmAction.tsx'
import { Alert, Badge, type Tone } from '../../../components/ui/Feedback.tsx'
import { ActivityIcon, StopIcon } from '../../../components/ui/icons.tsx'
import { stopAction } from '../api.ts'
import { isRunning, progressPct, tailLogs } from '../model.ts'
import type { Job } from '../schemas.ts'

const statusTone = (status: string | null | undefined): Tone =>
  status === 'running' ? 'success' : status === 'error' ? 'destructive' : 'secondary'

export function StopJob({ job, defaultOpen }: { job: Job; defaultOpen?: boolean }) {
  const stop = useAction(stopAction)
  return (
    <>
      <ConfirmAction
        icon={StopIcon}
        label={m.job_stop()}
        title={m.job_stop_title()}
        details={job.mode === 'auto' ? m.job_stop_auto_details() : m.job_stop_custom_details()}
        confirmLabel={m.job_stop()}
        disabled={!isRunning(job) || stop.isPending}
        defaultOpen={defaultOpen}
        onConfirm={() => stop.mutate()}
      />
      <ActionStatus action={stop} />
    </>
  )
}

function Progress({ pct }: { pct: number }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-muted" role="progressbar"
      aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
      <div className="h-full rounded-full bg-primary transition-[width]"
        style={{ width: `${pct}%` }} />
    </div>
  )
}

export function JobStatus({ job }: { job: Job }) {
  const fmt = useFormat()
  const pct = progressPct(job)
  return (
    <Card testId="job-status">
      <CardHeader
        icon={ActivityIcon}
        title={m.job_status_title()}
        description={m.job_state({
          mode: enumLabel('mode', job.mode),
          status: enumLabel('status', job.status),
          phase: enumLabel('phase', job.phase),
        })}
        actions={(
          <>
            <Badge tone={statusTone(job.status)}>{enumLabel('status', job.status)}</Badge>
            <StopJob job={job} />
          </>
        )}
      />
      <CardContent className="space-y-3 text-sm">
        <p className="flex flex-wrap justify-between gap-2 tabular-nums">
          <span>{m.job_progress({
            round: job.round ?? 0,
            tf: job.current_tf ?? '-',
            symbol: job.current_symbol ?? '-',
            current: job.current ?? 0,
            total: job.total ?? 0,
          })}</span>
          {pct !== null && <span className="font-medium">{`${pct}%`}</span>}
        </p>
        {pct !== null && <Progress pct={pct} />}
        {job.cooldown_until && (
          <p className="text-muted-foreground">
            {m.job_cooldown({ until: fmt.dateTime(job.cooldown_until) })}
          </p>
        )}
        {job.message && (
          <p>{codeMessage(job.message_code ?? null, job.message_params ?? {}) ?? job.message}</p>
        )}
        {(job.failed?.length ?? 0) > 0 && (
          <Alert tone="destructive">{m.job_failed({ list: (job.failed ?? []).join(', ') })}</Alert>
        )}
        <details className="group rounded-lg border">
          <summary className="cursor-pointer px-3 py-2 font-medium">{m.job_logs()}</summary>
          <pre className="max-h-60 overflow-auto border-t bg-muted/40 p-3 font-mono text-xs"
            data-testid="job-logs">
            {tailLogs(job).join('\n')}
          </pre>
        </details>
      </CardContent>
    </Card>
  )
}
