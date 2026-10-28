import { cn } from './cn.ts'

/** On/off switch. It only reports the wish to change; callers that change server state put
 * a confirm step in between and keep `checked` on the saved value. */
export function Switch({ checked, onChange, label, disabled, testId }: {
  checked: boolean
  onChange: (next: boolean) => void
  label: string
  disabled?: boolean
  testId?: string
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      data-testid={testId}
      onClick={() => onChange(!checked)}
      className={cn('inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full',
        'border-2 border-transparent shadow-sm transition-colors disabled:cursor-not-allowed',
        'disabled:opacity-50', checked ? 'bg-primary' : 'bg-input')}
    >
      <span className={cn('block size-4 rounded-full bg-background shadow transition-transform',
        checked ? 'translate-x-4' : 'translate-x-0')} />
    </button>
  )
}
