import { useState, type ReactNode } from 'react'
import { m } from '../../paraglide/messages.js'
import { Dialog } from './Dialog.tsx'
import { Spinner } from './Feedback.tsx'
import { button, type ButtonSize, type ButtonVariant } from './form.ts'
import type { IconComponent } from './icons.tsx'

/** Create/edit form in a modal: a trigger button opens it; `onSubmit` gets `close` so the
 * dialog shuts only once the write succeeded (errors stay visible with the inputs). */
export function FormDialog({
  triggerLabel, title, description, submitLabel, pending = false, onSubmit, children,
  icon: Icon, iconOnly = false, variant = 'default', size = 'md', defaultOpen = false, testId,
  disabled,
}: {
  triggerLabel: string
  title: string
  description?: ReactNode
  submitLabel: string
  pending?: boolean
  onSubmit: (close: () => void) => void
  children: ReactNode
  icon?: IconComponent
  iconOnly?: boolean
  variant?: ButtonVariant
  size?: ButtonSize
  /** Tests server-render the open dialog directly. */
  defaultOpen?: boolean
  testId?: string
  disabled?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  const close = () => setOpen(false)
  return (
    <>
      <button
        type="button"
        className={button(iconOnly ? 'ghost' : variant, iconOnly ? 'icon-sm' : size)}
        aria-label={iconOnly ? triggerLabel : undefined}
        title={iconOnly ? triggerLabel : undefined}
        disabled={disabled}
        onClick={() => setOpen(true)}
      >
        {Icon && <Icon />}
        {!iconOnly && triggerLabel}
      </button>
      <Dialog
        open={open}
        onClose={close}
        title={title}
        description={description}
        testId={testId}
        onSubmit={(e) => {
          e.preventDefault()
          onSubmit(close)
        }}
        footer={(
          <>
            <button type="button" className={button('outline')} onClick={close}>
              {m.confirm_cancel()}
            </button>
            <button type="submit" className={button('default')} disabled={pending}>
              {pending && <Spinner />}
              {submitLabel}
            </button>
          </>
        )}
      >
        <div className="space-y-4">{children}</div>
      </Dialog>
    </>
  )
}
