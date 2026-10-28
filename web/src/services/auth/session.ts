// Every piece of session handling for the new UI lives here. The session is the HttpOnly
// cookie the backend sets at sign-in (plus the readable CSRF cookie the API client echoes);
// this code never sees a token. The legacy UI has its own login and token and is not used.
import { csrfHeaders } from '../api/csrf.ts'
import { apiUrl } from '../api/url.ts'
import { appEnv } from '../../config/env.ts'

/** The new UI's sign-in page, under the app base (e.g. /app/login/). */
export const loginPath = (): string => `${appEnv.appBase}login/`

function goToLogin(): void {
  const login = loginPath()
  if (globalThis.location && !globalThis.location.pathname.startsWith(login)) {
    globalThis.location.href = login
  }
}

/** Ends the session on the server (revokes it, clears the cookies), then shows sign-in.
 * `keepalive` lets the request finish even though the page navigates right after. */
export async function logout(): Promise<void> {
  try {
    await fetch(apiUrl('auth/logout'), {
      method: 'POST',
      credentials: 'include',
      keepalive: true,
      headers: { Accept: 'application/json', ...csrfHeaders() },
    })
  } catch {
    // offline: the session still expires on its own
  }
  goToLogin()
}

/** Called by the API client on HTTP 401: the server already refused the session. */
export function onUnauthorized(): void {
  goToLogin()
}
