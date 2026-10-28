import { describe, expect, it } from 'vitest'
import { MOCK_PASSWORD, MOCK_USER, db } from '../../testing/mocks/db.ts'
import { runWithCache } from '../../testing/mocks/actionHarness.ts'
import { renderPage } from '../../testing/mocks/renderPage.tsx'
import { authStatusQuery, signInAction, signInMode } from './api.ts'
import { LoginPage } from './index.ts'

describe('auth', () => {
  it('offers register only on a first run the server allows', () => {
    expect(signInMode({ registered: true })).toBe('login')
    expect(signInMode({ registered: false, registration_open: false })).toBe('login')
    expect(signInMode({ registered: false, registration_open: true })).toBe('register')
  })

  it('signs in, and a wrong password is a translated error code', async () => {
    const credentials = { username: MOCK_USER, password: MOCK_PASSWORD }
    const ok = await runWithCache(signInAction, { mode: 'login', credentials },
      [authStatusQuery.queryKey])
    expect(ok.data.status).toBe('ok')
    await expect(runWithCache(signInAction,
      { mode: 'login', credentials: { ...credentials, password: 'nope' } }, []))
      .rejects.toMatchObject({ status: 401, code: 'auth.bad_credentials' })
  })

  it('first-run register enforces the server minimum', async () => {
    db.registered = false
    await expect(runWithCache(signInAction,
      { mode: 'register', credentials: { username: 'new', password: 'short' } }, []))
      .rejects.toMatchObject({ code: 'auth.password_short', params: { min: 12 } })
  })

  it('renders the form from the cached status', () => {
    const html = renderPage(<LoginPage />, [[authStatusQuery.queryKey, { registered: true }]])
    expect(html).toContain('data-testid="login-form"')
    expect(html).toContain('type="password"')
  })
})
