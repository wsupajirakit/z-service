import { useState } from 'react'
import { m } from '../../../paraglide/messages.js'
import { useAction } from '../../../services/api/action.ts'
import { ActionStatus } from '../../../components/ui/ActionStatus.tsx'
import { Card, CardContent, CardHeader } from '../../../components/ui/Card.tsx'
import { button, fieldClass, fieldErrorClass, inputClass } from '../../../components/ui/form.ts'
import { UserIcon } from '../../../components/ui/icons.tsx'
import { changePasswordAction } from '../api.ts'

const EMPTY = { current: '', next: '', confirm: '' }

/** Change the password. Length rules live on the server (its error says the minimum);
 * the form only checks that the new password was typed the same way twice. */
export function PasswordSettings() {
  const save = useAction(changePasswordAction, { success: () => m.password_changed() })
  const [form, setForm] = useState(EMPTY)
  const mismatch = form.confirm !== '' && form.next !== form.confirm
  const ready = form.current !== '' && form.next !== '' && form.next === form.confirm
  const field = (key: keyof typeof EMPTY, label: string, auto: string) => (
    <label className={fieldClass}>
      {label}
      <input className={inputClass} type="password" autoComplete={auto} value={form[key]}
        aria-invalid={key === 'confirm' && mismatch}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })} />
    </label>
  )
  return (
    <Card>
      <CardHeader icon={UserIcon} title={m.settings_password()} description={m.password_hint()} />
      <CardContent>
        <form className="max-w-md space-y-4" data-testid="password-form" onSubmit={(e) => {
          e.preventDefault()
          if (ready) {
            save.mutate({ current: form.current, next: form.next },
              { onSuccess: () => setForm(EMPTY) })
          }
        }}>
          {field('current', m.password_current(), 'current-password')}
          {field('next', m.password_new(), 'new-password')}
          {field('confirm', m.password_confirm(), 'new-password')}
          {mismatch && <p className={fieldErrorClass} role="alert">{m.password_mismatch()}</p>}
          <button type="submit" className={button('default')} disabled={!ready || save.isPending}>
            {m.action_save()}
          </button>
          <ActionStatus action={save} />
        </form>
      </CardContent>
    </Card>
  )
}
