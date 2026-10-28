import { afterEach, describe, expect, it, vi } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '../../testing/mocks/testServer.ts'
import { apiPattern } from '../api/url.ts'
import { appEnv } from '../../config/env.ts'
import { loginPath, logout, onUnauthorized } from './session.ts'

describe('session', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('the sign-in page lives under the app base', () => {
    expect(loginPath()).toBe(`${appEnv.appBase}login/`)
  })

  it('logout ends the session on the server before showing sign-in', async () => {
    let called = 0
    server.use(http.post(apiPattern('auth/logout'), () => {
      called += 1
      return HttpResponse.json({ status: 'ok', revoked: true })
    }))
    const location = { pathname: `${appEnv.appBase}settings/`, href: '' }
    vi.stubGlobal('location', location)
    await logout()
    expect(called).toBe(1)
    expect(location.href).toBe(loginPath())
  })

  it('a 401 goes to sign-in without another request, and not in a loop', () => {
    const fetchSpy = vi.fn()
    vi.stubGlobal('fetch', fetchSpy)
    const location = { pathname: loginPath(), href: '' }
    vi.stubGlobal('location', location)
    onUnauthorized()
    expect(fetchSpy).not.toHaveBeenCalled()
    expect(location.href).toBe('')
  })
})
