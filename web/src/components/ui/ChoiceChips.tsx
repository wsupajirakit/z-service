import type { ReactNode } from 'react'
import { toggle } from '../../utils/symbols.ts'
import { cn } from './cn.ts'

/** A checkbox drawn as a toggle chip (the box itself is visually hidden, still focusable). */
export function Chip({ checked, onChange, children, title }: {
  checked: boolean
  onChange: (next: boolean) => void
  children: ReactNode
  title?: string
}) {
  return (
    <label title={title}
      className={cn('inline-flex cursor-pointer items-center gap-1.5 rounded-md border px-2.5',
        'py-1 text-xs font-medium transition-colors has-[:focus-visible]:ring-2',
        'has-[:focus-visible]:ring-ring',
        checked ? 'border-primary bg-primary/10 text-primary' : 'hover:bg-accent')}>
      <input type="checkbox" className="sr-only" checked={checked}
        onChange={(e) => onChange(e.target.checked)} />
      {children}
    </label>
  )
}

/** Multi-select over a short fixed list (timeframes, formulas). */
export function ChipGroup({ legend, options, value, onChange }: {
  legend: string
  options: readonly string[]
  value: string[]
  onChange: (next: string[]) => void
}) {
  return (
    <fieldset className="space-y-2">
      <legend className="text-sm font-medium">{legend}</legend>
      <div className="flex flex-wrap gap-1.5">
        {options.map((x) => (
          <Chip key={x} checked={value.includes(x)}
            onChange={(on) => onChange(toggle(value, x, on))}>
            {x}
          </Chip>
        ))}
      </div>
    </fieldset>
  )
}
