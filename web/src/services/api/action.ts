// Write actions: a request function plus the queries it makes stale. Pages call useAction();
// tests call runAction() with their own QueryClient, so invalidation is tested without a DOM.
// Every result is reported as a toast from the hook-level callbacks, which TanStack Query runs
// even when the calling component has unmounted (e.g. a removed row or a closed dialog).
import { useMutation, useQueryClient, type QueryClient, type QueryKey } from '@tanstack/react-query'
import { m } from '../../paraglide/messages.js'
import { showToast } from '../../stores/toast.ts'
import { errorText } from './errorMessages.ts'

export type Action<V, D> = {
  run: (vars: V) => Promise<D>
  /** Query keys (prefix match) refetched after success. */
  invalidates: readonly QueryKey[]
}

/** How a page reports an action's result: its own success text, or no toast at all (the page
 * shows the outcome itself, e.g. the sign-in form). */
export type ActionNotice<D> = { success?: (data: D) => string; silent?: boolean }

export function defineAction<V, D>(
  run: (vars: V) => Promise<D>,
  invalidates: readonly QueryKey[],
): Action<V, D> {
  return { run, invalidates }
}

export async function runAction<V, D>(client: QueryClient, action: Action<V, D>, vars: V) {
  const data = await action.run(vars)
  await Promise.all(action.invalidates.map((queryKey) => client.invalidateQueries({ queryKey })))
  return data
}

export function notifySuccess<D>(notice: ActionNotice<D>, data: D): void {
  if (!notice.silent) showToast('success', notice.success?.(data) || m.action_done())
}

export function notifyError(notice: Pick<ActionNotice<never>, 'silent'>, error: unknown): void {
  if (!notice.silent) showToast('error', errorText(error))
}

export function useAction<V, D>(action: Action<V, D>, notice: ActionNotice<D> = {}) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (vars: V) => runAction(client, action, vars),
    onSuccess: (data) => notifySuccess(notice, data),
    onError: (error) => notifyError(notice, error),
  })
}
