import { m } from '../../../paraglide/messages.js'
import { replyText } from '../../../services/api/common.ts'
import { codeMessage } from '../../../services/api/errorMessages.ts'
import { useAction } from '../../../services/api/action.ts'
import { useFormat } from '../../../hooks/useFormat.ts'
import { ActionStatus } from '../../../components/ui/ActionStatus.tsx'
import { Card, CardContent, CardFooter, CardHeader } from '../../../components/ui/Card.tsx'
import { ConfirmAction } from '../../../components/ui/ConfirmAction.tsx'
import { button } from '../../../components/ui/form.ts'
import { ActivityIcon, ExternalLinkIcon, PlayIcon, StopIcon } from
  '../../../components/ui/icons.tsx'
import { QueryState } from '../../../components/ui/QueryState.tsx'
import { startGoldAction, stopGoldAction, useGoldJob, type GoldRun } from '../api.ts'
import { goldRunning, safeExternalUrl } from '../model.ts'

export function GoldJobPanel({ run, defaultOpen }: { run: GoldRun; defaultOpen?: boolean }) {
  const fmt = useFormat()
  const job = useGoldJob()
  const start = useAction(startGoldAction)
  const stop = useAction(stopGoldAction, { success: (d) => replyText(d, m.action_done()) })
  const running = goldRunning(job.data)
  return (
    <Card testId="gold-job">
      <CardHeader icon={ActivityIcon} title={m.gold_job_title()}
        description={m.gold_job_description()} />
      <CardContent>
        <QueryState query={job}>
          {(j) => {
            const link = safeExternalUrl(j.folder_link)
            return (
              <div className="space-y-2 text-sm">
                <p>{m.gold_job_state({ status: j.status, at: fmt.dateTime(j.finished_at
                  ?? j.started_at) })}</p>
                {j.message && (
                  <p className="text-muted-foreground">
                    {codeMessage(j.message_code ?? null, j.message_params ?? {}) ?? j.message}
                  </p>
                )}
                {link && (
                  <a className={button('link', 'sm')} href={link} rel="noopener noreferrer"
                    target="_blank">
                    {j.folder_name ?? link}
                    <ExternalLinkIcon size={14} />
                  </a>
                )}
              </div>
            )
          }}
        </QueryState>
      </CardContent>
      <CardFooter>
        <ConfirmAction
          tone="cost"
          variant="default"
          icon={PlayIcon}
          label={m.gold_job_start()}
          title={m.gold_job_start()}
          details={m.gold_job_start_details({ exchange: run.exchange, model: run.model })}
          confirmLabel={m.gold_job_start()}
          disabled={running || !run.model || start.isPending}
          defaultOpen={defaultOpen}
          onConfirm={() => start.mutate(run)}
        />
        <ConfirmAction
          variant="outline"
          icon={StopIcon}
          label={m.gold_job_stop()}
          title={m.gold_job_stop()}
          details={m.gold_job_stop_details()}
          confirmLabel={m.gold_job_stop()}
          disabled={!running || stop.isPending}
          onConfirm={() => stop.mutate()}
        />
        <ActionStatus action={start} />
        <ActionStatus action={stop} />
      </CardFooter>
    </Card>
  )
}
