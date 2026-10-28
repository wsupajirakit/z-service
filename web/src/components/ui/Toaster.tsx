import { useEffect, useRef, useSyncExternalStore } from 'react'
import { m } from '../../paraglide/messages.js'
import { dismissToast, getToasts, subscribeToasts, type Toast } from '../../stores/toast.ts'
import { cn } from './cn.ts'
import { button } from './form.ts'
import { AlertIcon, CircleCheckIcon, InfoIcon, XIcon } from './icons.tsx'

const look = {
  success: { icon: CircleCheckIcon, className: 'text-up' },
  error: { icon: AlertIcon, className: 'text-destructive' },
  info: { icon: InfoIcon, className: 'text-primary' },
} as const

function ToastItem({ toast }: { toast: Toast }) {
  const { icon: Icon, className } = look[toast.tone]
  return (
    <li
      role={toast.tone === 'error' ? 'alert' : 'status'}
      className="zs-toast pointer-events-auto flex w-full items-start gap-3 rounded-lg border
        bg-popover p-4 text-sm text-popover-foreground shadow-lg"
      data-testid="toast"
      data-tone={toast.tone}
    >
      <Icon className={cn('mt-0.5', className)} />
      <p className="min-w-0 flex-1 break-words">{toast.text}</p>
      <button type="button" className={cn(button('ghost', 'icon-xs'), '-my-0.5 -mr-1')}
        aria-label={m.toast_dismiss()} onClick={() => dismissToast(toast.id)}>
        <XIcon size={14} />
      </button>
    </li>
  )
}

/** Result messages of write actions (bottom right; top on small screens). The region is a
 * manual popover so it sits in the top layer: re-showing it after each change keeps it above
 * an open modal dialog, whose own result would otherwise be hidden behind the backdrop. */
export function Toaster() {
  const toasts = useSyncExternalStore(subscribeToasts, getToasts, getToasts)
  const ref = useRef<HTMLElement>(null)
  useEffect(() => {
    const el = ref.current
    if (!el?.showPopover) return
    const open = el.matches(':popover-open')
    // Re-showing restarts the enter animation, so only do it to climb above a modal.
    if (open && (toasts.length === 0 || document.querySelector('dialog[open]'))) el.hidePopover()
    if (toasts.length > 0 && !el.matches(':popover-open')) el.showPopover()
  }, [toasts])
  return (
    <section ref={ref} popover="manual" aria-label={m.toast_region()}
      className="pointer-events-none fixed inset-x-0 top-0 bottom-auto z-50 m-0 flex h-auto w-full
        max-w-none justify-center overflow-visible border-0 bg-transparent p-4 sm:top-auto
        sm:bottom-0 sm:justify-end">
      <ol className="flex w-full max-w-sm flex-col gap-2">
        {toasts.map((t) => <ToastItem key={t.id} toast={t} />)}
      </ol>
    </section>
  )
}
