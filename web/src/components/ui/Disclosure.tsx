import type { ReactNode } from 'react'
import { ChevronRightIcon } from './icons.tsx'

/** Collapsible row (native <details>) for lists of past runs. */
export function Disclosure({ summary, children, testId }: {
  summary: ReactNode
  children: ReactNode
  testId?: string
}) {
  return (
    <details className="group rounded-xl border bg-card text-card-foreground shadow-sm"
      data-testid={testId}>
      <summary className="flex cursor-pointer list-none items-center gap-3 px-5 py-3.5 text-sm
        [&::-webkit-details-marker]:hidden">
        <ChevronRightIcon className="text-muted-foreground transition-transform
          group-open:rotate-90" />
        <span className="flex min-w-0 flex-1 flex-wrap items-center gap-x-3 gap-y-1">
          {summary}
        </span>
      </summary>
      <div className="space-y-3 border-t px-5 py-4">{children}</div>
    </details>
  )
}
