// Pure job logic: poll rate, progress text inputs, which buttons make sense.
import { appConfig } from '../../config/app.ts'
import type { Job } from './schemas.ts'

export const isRunning = (job: Job | undefined) => job?.status === 'running'

export function jobPollMs(job: Job | undefined): number {
  return isRunning(job) ? appConfig.poll.jobRunning : appConfig.poll.jobIdle
}

/** 0..100 progress of the current step, or null when unknown. */
export function progressPct(job: Job): number | null {
  const { current, total } = job
  if (!total || current === undefined) return null
  return Math.min(100, Math.round((current / total) * 100))
}

/** Newest log lines last, capped for display. */
export const tailLogs = (job: Job, n = 20) => (job.logs ?? []).slice(-n)

/** Columns of a bar table: datetime first, then OHLCV, then the rest in server order. */
export function barColumns(rows: ReadonlyArray<Record<string, unknown>>): string[] {
  const first = ['datetime', 'open', 'high', 'low', 'close', 'volume']
  const seen = new Set<string>()
  for (const r of rows) Object.keys(r).forEach((k) => seen.add(k))
  return [...first.filter((k) => seen.has(k)), ...[...seen].filter((k) => !first.includes(k))]
}
