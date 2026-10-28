import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { m } from '../../../paraglide/messages.js'
import { useAction } from '../../../services/api/action.ts'
import { appEnv } from '../../../config/env.ts'
import { Card, CardContent, CardHeader } from '../../../components/ui/Card.tsx'
import { Alert, Spinner } from '../../../components/ui/Feedback.tsx'
import { button, fieldClass, hintClass, inputClass } from '../../../components/ui/form.ts'
import { UserIcon } from '../../../components/ui/icons.tsx'
import { errorText } from '../../../services/api/errorMessages.ts'
import { QueryState } from '../../../components/ui/QueryState.tsx'
import { authStatusQuery, signInAction, signInMode, type SignInMode } from '../api.ts'

function SignInForm({ mode }: { mode: SignInMode }) {
  // The form shows its own error and navigates away on success: no toast.
  const signIn = useAction(signInAction, { silent: true })
  const [form, setForm] = useState({ username: '', password: '' })
  const ready = form.username.trim() !== '' && form.password !== ''
  return (
    <form
      className="space-y-4"
      data-testid="login-form"
      onSubmit={(e) => {
        e.preventDefault()
        if (!ready) return
        const credentials = { username: form.username.trim(), password: form.password }
        signIn.mutate({ mode, credentials }, {
          onSuccess: () => { globalThis.location.href = appEnv.appBase },
        })
      }}
    >
      {mode === 'register' && <p className={hintClass}>{m.register_hint()}</p>}
      <label className={fieldClass}>
        {m.login_username()}
        <input className={inputClass} autoComplete="username" value={form.username}
          onChange={(e) => setForm({ ...form, username: e.target.value })} />
      </label>
      <label className={fieldClass}>
        {m.login_password()}
        <input className={inputClass} type="password" value={form.password}
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          onChange={(e) => setForm({ ...form, password: e.target.value })} />
      </label>
      {signIn.isError && <Alert tone="destructive">{errorText(signIn.error)}</Alert>}
      <button type="submit" className={`${button('default')} w-full`}
        disabled={!ready || signIn.isPending}>
        {signIn.isPending && <Spinner />}
        {mode === 'login' ? m.login_submit() : m.register_submit()}
      </button>
    </form>
  )
}

/** The new UI's own sign-in page (public route); the legacy UI keeps its own /login. */
export function LoginPage() {
  const status = useQuery(authStatusQuery)
  const mode = status.data ? signInMode(status.data) : 'login'
  return (
    <div className="mx-auto mt-[10vh] w-full max-w-sm">
      <Card>
        <CardHeader icon={UserIcon}
          title={mode === 'login' ? m.login_title() : m.register_title()}
          description={m.login_description()} />
        <CardContent>
          <QueryState query={status}>{(s) => <SignInForm mode={signInMode(s)} />}</QueryState>
        </CardContent>
      </Card>
    </div>
  )
}
