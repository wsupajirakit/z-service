import type { ReactNode } from 'react'

/** Intro line and page-level actions under the shell header (which holds the page title). */
export function PageHeader({ description, children }: {
  description?: string
  children?: ReactNode
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      {description && <p className="max-w-3xl text-sm text-muted-foreground">{description}</p>}
      {children && <div className="ml-auto flex flex-wrap items-center gap-2">{children}</div>}
    </div>
  )
}
