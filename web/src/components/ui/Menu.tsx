// Small dropdown menu (header language and account menus). Closes on Escape, on a click
// outside and after a choice; focus returns to the trigger.
import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { cn } from './cn.ts'
import { button } from './form.ts'
import { CheckIcon } from './icons.tsx'

export type MenuItem = {
  key: string
  label: ReactNode
  onSelect: () => void
  /** Radio-style item (e.g. the current language). */
  checked?: boolean
  icon?: ReactNode
  destructive?: boolean
}

export function Menu({ trigger, label, items, header, testId }: {
  trigger: ReactNode
  /** Accessible name of the trigger button. */
  label: string
  items: MenuItem[]
  header?: ReactNode
  testId?: string
}) {
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const id = useId()
  useEffect(() => {
    if (!open) return
    const onDown = (e: PointerEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      setOpen(false)
      triggerRef.current?.focus()
    }
    document.addEventListener('pointerdown', onDown)
    document.addEventListener('keydown', onKey)
    root.current?.querySelector<HTMLElement>('[role^=menuitem]')?.focus()
    return () => {
      document.removeEventListener('pointerdown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])
  const radio = items.some((i) => i.checked !== undefined)
  return (
    <div ref={root} className="relative" data-testid={testId}>
      <button ref={triggerRef} type="button" className={button('ghost', 'sm')}
        aria-label={label} title={label} aria-haspopup="menu" aria-expanded={open}
        aria-controls={id} onClick={() => setOpen(!open)}>
        {trigger}
      </button>
      {open && (
        <div id={id} role="menu" aria-label={label}
          className="absolute top-full right-0 z-40 mt-1 min-w-44 rounded-lg border bg-popover
            p-1 text-popover-foreground shadow-lg">
          {header && <div className="border-b px-2 py-1.5 text-xs text-muted-foreground">
            {header}</div>}
          {items.map((item) => (
            <button
              key={item.key}
              type="button"
              role={radio ? 'menuitemradio' : 'menuitem'}
              aria-checked={radio ? item.checked === true : undefined}
              className={cn('flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left',
                'text-sm hover:bg-accent focus-visible:bg-accent focus-visible:outline-none',
                item.destructive && 'text-destructive')}
              onClick={() => {
                setOpen(false)
                triggerRef.current?.focus()
                item.onSelect()
              }}
            >
              {item.icon}
              <span className="flex-1">{item.label}</span>
              {item.checked && <CheckIcon size={14} className="text-primary" />}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
