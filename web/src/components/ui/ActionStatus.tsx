import { m } from '../../paraglide/messages.js'
import { Spinner } from './Feedback.tsx'

/** "Working…" next to a write action while it runs; the result itself arrives as a toast
 * (see useAction). */
export function ActionStatus({ action }: { action: { isPending: boolean } }) {
  if (!action.isPending) return null
  return (
    <p className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
      <Spinner />
      {m.action_running()}
    </p>
  )
}
