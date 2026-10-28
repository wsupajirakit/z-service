import { useId, useState, type ReactNode } from 'react'
import { m } from '../../paraglide/messages.js'
import { Modal } from './Dialog.tsx'
import { button, type ButtonSize, type ButtonVariant } from './form.ts'
import { AlertIcon, type IconComponent } from './icons.tsx'

export type ConfirmTone = 'danger' | 'cost' | 'normal'

const confirmVariant = (tone: ConfirmTone): ButtonVariant =>
  (tone === 'normal' ? 'default' : 'destructive')

/** Themed confirm step (alert dialog): says exactly what will happen, then confirm or cancel. */
export function ConfirmDialog({
  open, title, details, confirmLabel, tone, onConfirm, onCancel, disabled,
}: {
  open: boolean
  title: string
  details: ReactNode
  confirmLabel: string
  tone: ConfirmTone
  onConfirm: () => void
  onCancel: () => void
  /** Inputs changed after the first click and are no longer valid. */
  disabled?: boolean
}) {
  const id = useId()
  return (
    <Modal open={open} onClose={onCancel} role="alertdialog" labelledBy={`${id}-t`}
      describedBy={`${id}-d`} look="md">
      <div className="space-y-4 p-6" data-testid="confirm-panel">
        <div className="flex gap-3">
          {tone !== 'normal' && (
            <span className="h-fit rounded-full bg-destructive/15 p-2 text-destructive">
              <AlertIcon />
            </span>
          )}
          <div className="min-w-0 space-y-2">
            <h2 id={`${id}-t`} className="text-lg leading-tight font-semibold">{title}</h2>
            {tone === 'cost' && (
              <p className="text-sm font-medium text-destructive" data-testid="cost-warning">
                {m.confirm_cost()}
              </p>
            )}
            <div id={`${id}-d`} className="text-sm break-words text-muted-foreground">
              {details}
            </div>
          </div>
        </div>
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <button type="button" className={button('outline')} onClick={onCancel}>
            {m.confirm_cancel()}
          </button>
          <button type="button" className={button(confirmVariant(tone))} disabled={disabled}
            onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </Modal>
  )
}

/** Button for destructive, state-changing or costly actions: click, read, confirm. */
export function ConfirmAction({
  label, title, details, confirmLabel, tone = 'danger', disabled, onConfirm, defaultOpen = false,
  icon: Icon, iconOnly = false, variant, size = 'md',
}: {
  label: string
  title: string
  details: ReactNode
  confirmLabel: string
  tone?: ConfirmTone
  disabled?: boolean
  onConfirm: () => void
  /** Tests server-render the second step directly. */
  defaultOpen?: boolean
  icon?: IconComponent
  /** Row actions: only the icon shows; the label becomes its accessible name. */
  iconOnly?: boolean
  variant?: ButtonVariant
  size?: ButtonSize
}) {
  const [open, setOpen] = useState(defaultOpen)
  const look = variant ?? (iconOnly ? 'ghost' : confirmVariant(tone))
  return (
    <>
      <button
        type="button"
        className={button(look, iconOnly ? 'icon-sm' : size)}
        disabled={disabled || open}
        aria-label={iconOnly ? label : undefined}
        title={iconOnly ? label : undefined}
        onClick={() => setOpen(true)}
      >
        {Icon && <Icon />}
        {!iconOnly && label}
      </button>
      <ConfirmDialog
        open={open}
        title={title}
        details={details}
        confirmLabel={confirmLabel}
        tone={tone}
        disabled={disabled}
        onCancel={() => setOpen(false)}
        onConfirm={() => {
          setOpen(false)
          onConfirm()
        }}
      />
    </>
  )
}
