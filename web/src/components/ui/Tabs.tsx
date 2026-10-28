import type { KeyboardEvent, ReactNode } from 'react'
import { cn } from './cn.ts'

export type TabItem<V extends string> = { value: V; label: ReactNode }

/** Ids that tie a tab to its panel (aria-controls / aria-labelledby). */
export const tabIds = (base: string, value: string) =>
  ({ tab: `${base}-tab-${value}`, panel: `${base}-panel-${value}` })

/** Segmented tab list (shadcn look). Arrow keys move between tabs; the caller renders the
 * panel for the selected value (with `idBase`, under the ids from tabIds). */
export function Tabs<V extends string>({ items, value, onChange, label, testId, idBase }: {
  items: TabItem<V>[]
  value: V
  onChange: (value: V) => void
  label: string
  testId?: string
  idBase?: string
}) {
  const move = (e: KeyboardEvent<HTMLDivElement>) => {
    const step = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0
    if (step === 0) return
    const index = items.findIndex((t) => t.value === value)
    const next = items[(index + step + items.length) % items.length]
    if (next) onChange(next.value)
  }
  return (
    <div role="tablist" aria-label={label} onKeyDown={move} data-testid={testId}
      className="inline-flex max-w-full flex-wrap items-center gap-1 rounded-lg bg-muted p-1
        text-muted-foreground">
      {items.map((t) => (
        <button
          key={t.value}
          type="button"
          role="tab"
          id={idBase && tabIds(idBase, t.value).tab}
          aria-controls={idBase && tabIds(idBase, t.value).panel}
          aria-selected={t.value === value}
          tabIndex={t.value === value ? 0 : -1}
          onClick={() => onChange(t.value)}
          className={cn('inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-sm',
            'font-medium whitespace-nowrap transition-colors',
            t.value === value
              ? 'bg-background text-foreground shadow-sm'
              : 'hover:text-foreground')}
        >
          {t.label}
        </button>
      ))}
    </div>
  )
}
