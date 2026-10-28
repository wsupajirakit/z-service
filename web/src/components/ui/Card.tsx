import type { ReactNode } from 'react'
import { cn } from './cn.ts'
import type { IconComponent } from './icons.tsx'

type Box = { className?: string; children?: ReactNode; testId?: string }

export function Card({ className, children, testId }: Box) {
  return (
    <section
      className={cn('rounded-xl border bg-card text-card-foreground shadow-sm', className)}
      data-testid={testId}
    >
      {children}
    </section>
  )
}

/** Title row of a card, with optional description and actions on the right. */
export function CardHeader({ title, description, actions, icon: Icon }: {
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
  icon?: IconComponent
}) {
  return (
    <header className="flex flex-wrap items-start gap-3 px-5 pt-5 pb-3">
      {Icon && (
        <span className="mt-0.5 rounded-md bg-primary/10 p-1.5 text-primary"><Icon /></span>
      )}
      <div className="min-w-0 flex-1 space-y-1">
        <h2 className="leading-none font-semibold tracking-tight">{title}</h2>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  )
}

export function CardContent({ className, children }: Box) {
  return <div className={cn('px-5 pb-5', className)}>{children}</div>
}

export function CardFooter({ className, children }: Box) {
  return (
    <footer className={cn('flex flex-wrap items-center gap-2 border-t px-5 py-3', className)}>
      {children}
    </footer>
  )
}

/** Summary number with its label (dashboard stat block). */
export function StatCard({ label, value, hint, icon: Icon, testId }: {
  label: string
  value: ReactNode
  hint?: ReactNode
  icon?: IconComponent
  testId?: string
}) {
  return (
    <Card className="p-5" testId={testId}>
      <div className="flex items-center justify-between gap-2 text-sm text-muted-foreground">
        <span className="font-medium">{label}</span>
        {Icon && <Icon className="text-primary" />}
      </div>
      <div className="mt-2 text-2xl font-semibold tracking-tight tabular-nums">{value}</div>
      {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
    </Card>
  )
}

export function StatGrid({ children }: { children: ReactNode }) {
  return <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{children}</div>
}
