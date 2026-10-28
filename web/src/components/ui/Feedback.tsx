// Small status pieces: badges, alerts, spinner, skeleton, empty state.
import type { ReactNode } from 'react'
import { m } from '../../paraglide/messages.js'
import { cn } from './cn.ts'
import { AlertIcon, CircleCheckIcon, InboxIcon, InfoIcon, LoaderIcon } from './icons.tsx'

export type Tone = 'default' | 'secondary' | 'outline' | 'success' | 'warning' | 'destructive'

const badgeTone: Record<Tone, string> = {
  default: 'border-transparent bg-primary text-primary-foreground',
  secondary: 'border-transparent bg-secondary text-secondary-foreground',
  outline: 'text-foreground',
  success: 'border-transparent bg-up/15 text-up',
  warning: 'border-transparent bg-warning/15 text-warning',
  destructive: 'border-transparent bg-destructive/15 text-destructive',
}

export function Badge({ tone = 'secondary', children, testId }: {
  tone?: Tone
  children: ReactNode
  testId?: string
}) {
  return (
    <span
      className={cn('inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs',
        'font-medium whitespace-nowrap', badgeTone[tone])}
      data-testid={testId}
    >
      {children}
    </span>
  )
}

type AlertTone = 'info' | 'success' | 'warning' | 'destructive'
const alertTone: Record<AlertTone, string> = {
  info: 'border-border bg-muted/40 text-foreground',
  success: 'border-up/40 bg-up/10 text-up',
  warning: 'border-warning/40 bg-warning/10 text-warning',
  destructive: 'border-destructive/40 bg-destructive/10 text-destructive',
}
const alertIcon = { info: InfoIcon, success: CircleCheckIcon, warning: AlertIcon,
  destructive: AlertIcon }

export function Alert({ tone = 'info', title, children, testId }: {
  tone?: AlertTone
  title?: ReactNode
  children?: ReactNode
  testId?: string
}) {
  const Icon = alertIcon[tone]
  return (
    <div
      role={tone === 'destructive' ? 'alert' : 'status'}
      className={cn('flex gap-3 rounded-lg border px-4 py-3 text-sm', alertTone[tone])}
      data-testid={testId}
    >
      <Icon className="mt-0.5" />
      <div className="min-w-0 space-y-1">
        {title && <p className="font-medium">{title}</p>}
        {children && <div className="text-foreground/80">{children}</div>}
      </div>
    </div>
  )
}

export function Spinner({ className }: { className?: string }) {
  return <LoaderIcon className={cn('animate-spin', className)} />
}

/** Placeholder rows while data loads. */
export function Skeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-2" role="status" aria-live="polite">
      <span className="sr-only">{m.state_loading()}</span>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="h-8 animate-pulse rounded-md bg-muted" />
      ))}
    </div>
  )
}

export function EmptyState({ title, children }: { title?: ReactNode; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border
      border-dashed px-6 py-10 text-center" data-testid="empty-state">
      <span className="rounded-full bg-muted p-3 text-muted-foreground">
        <InboxIcon size={20} />
      </span>
      <p className="text-sm font-medium">{title ?? m.state_empty()}</p>
      {children && <div className="text-sm text-muted-foreground">{children}</div>}
    </div>
  )
}
