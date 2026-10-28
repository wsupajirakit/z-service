// Modal dialogs on the native <dialog> element: showModal() gives the top layer, an inert
// page behind, focus moved inside and back, and Escape to close, with no runtime library.
// Content renders only while open, so server renders (tests) show exactly what is open.
import { useEffect, useId, useRef, type FormEvent, type ReactNode } from 'react'
import { m } from '../../paraglide/messages.js'
import { cn } from './cn.ts'
import { button } from './form.ts'
import { XIcon } from './icons.tsx'

type ModalProps = {
  open: boolean
  onClose: () => void
  children: ReactNode
  role?: 'dialog' | 'alertdialog'
  labelledBy?: string
  describedBy?: string
  /** center: dialog box (md for confirms, lg for forms); left: navigation drawer. */
  look?: 'md' | 'lg' | 'left'
  testId?: string
}

// Each look is complete on its own, so no class ever has to override another.
const looks = {
  md: 'm-auto w-[calc(100%-2rem)] max-w-md rounded-xl border bg-popover text-popover-foreground'
    + ' shadow-lg',
  lg: 'm-auto w-[calc(100%-2rem)] max-w-lg rounded-xl border bg-popover text-popover-foreground'
    + ' shadow-lg',
  left: 'm-0 h-dvh max-h-dvh w-72 max-w-[85vw] border-r border-sidebar-border bg-sidebar'
    + ' text-sidebar-foreground',
} as const

/** The <dialog> element itself; Dialog, ConfirmDialog and Sheet are built on it. */
export function Modal({
  open, onClose, children, role = 'dialog', labelledBy, describedBy, look = 'lg', testId,
}: ModalProps) {
  const ref = useRef<HTMLDialogElement>(null)
  // Set when a press starts on the backdrop, so a drag that ends there (text selection) does
  // not count as a click outside.
  const pressedBackdrop = useRef(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (open && !el.open) el.showModal()
    if (!open && el.open) el.close()
  }, [open])
  return (
    <dialog
      ref={ref}
      role={role === 'alertdialog' ? 'alertdialog' : undefined}
      aria-labelledby={labelledBy}
      aria-describedby={describedBy}
      data-side={look === 'left' ? 'left' : 'center'}
      data-testid={testId}
      className={cn('p-0', looks[look])}
      // Escape: let React state close it, so the open prop stays the single source of truth.
      onCancel={(e) => {
        e.preventDefault()
        onClose()
      }}
      // A press whose target is the <dialog> itself is on the backdrop (content fills the box).
      onPointerDown={(e) => {
        pressedBackdrop.current = e.target === e.currentTarget
      }}
      onClick={(e) => {
        if (pressedBackdrop.current && e.target === e.currentTarget) onClose()
        pressedBackdrop.current = false
      }}
    >
      {open && children}
    </dialog>
  )
}

/** Title, optional description, body and footer, with a close button. With `onSubmit` the
 * body and footer are one <form>, so Enter in a field submits it. */
export function Dialog({ open, onClose, title, description, children, footer, testId, onSubmit }: {
  open: boolean
  onClose: () => void
  title: ReactNode
  description?: ReactNode
  children?: ReactNode
  footer?: ReactNode
  testId?: string
  onSubmit?: (e: FormEvent<HTMLFormElement>) => void
}) {
  const id = useId()
  const inner = (
    <>
      <header className="flex items-start gap-3 px-6 pt-6 pb-2">
        <div className="min-w-0 flex-1 space-y-1.5">
          <h2 id={`${id}-t`} className="text-lg leading-none font-semibold">{title}</h2>
          {description && (
            <p id={`${id}-d`} className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>
        <button type="button" className={cn(button('ghost', 'icon-sm'), '-mt-2 -mr-2')}
          aria-label={m.dialog_close()} onClick={onClose}>
          <XIcon />
        </button>
      </header>
      <div className="overflow-y-auto px-6 py-3">{children}</div>
      {footer && (
        <footer className="flex flex-col-reverse gap-2 px-6 pt-2 pb-6 sm:flex-row sm:justify-end">
          {footer}
        </footer>
      )}
    </>
  )
  const frame = 'flex max-h-[85dvh] flex-col'
  return (
    <Modal open={open} onClose={onClose} labelledBy={`${id}-t`}
      describedBy={description ? `${id}-d` : undefined} testId={testId}>
      {onSubmit
        ? <form className={frame} onSubmit={onSubmit} noValidate>{inner}</form>
        : <div className={frame}>{inner}</div>}
    </Modal>
  )
}

/** Slide-in panel from the left (mobile navigation). */
export function Sheet({ open, onClose, title, children }: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
}) {
  const id = useId()
  return (
    <Modal open={open} onClose={onClose} look="left" labelledBy={id}>
      <div className="flex h-full flex-col">
        <div className="flex h-14 items-center justify-between border-b border-sidebar-border
          px-4">
          <h2 id={id} className="font-semibold">{title}</h2>
          <button type="button" className={button('ghost', 'icon-sm')}
            aria-label={m.dialog_close()} onClick={onClose}>
            <XIcon />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">{children}</div>
      </div>
    </Modal>
  )
}
