import { queryOptions } from '@tanstack/react-query'
import { defineAction } from '../../services/api/action.ts'
import { apiGet, apiSend } from '../../services/api/client.ts'
import { authStatusSchema, signedInSchema } from './schemas.ts'

export type Credentials = { username: string; password: string }
export type SignInMode = 'login' | 'register'

export const authStatusQuery = queryOptions({
  queryKey: ['auth', 'status'],
  queryFn: ({ signal }) => apiGet('auth/status', authStatusSchema, { signal }),
})

/** Login or first-run register; both answer with the session cookies. */
export const signInAction = defineAction(
  (v: { mode: SignInMode; credentials: Credentials }) =>
    v.mode === 'login'
      ? apiSend('post', 'auth/login', signedInSchema, { body: v.credentials })
      : apiSend('post', 'auth/register', signedInSchema, { body: v.credentials }),
  [authStatusQuery.queryKey],
)

/** Which form to show: register only on a first run the server allows. */
export function signInMode(status: { registered: boolean; registration_open?: boolean }) {
  return !status.registered && status.registration_open ? 'register' : 'login'
}
