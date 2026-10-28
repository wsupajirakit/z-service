// Auth endpoints. Mirrors zservice/domains/auth/routes.py: same status codes and error codes,
// minimum password length 12. The mock user signs in with MOCK_USER / MOCK_PASSWORD (db.ts).
import { http } from 'msw'
import { apiPattern } from '../../services/api/url.ts'
import { MOCK_USER, db } from './db.ts'
import { fail, jsonBody, ok, str } from './reply.ts'

const p = apiPattern
const PASSWORD_MIN = 12
const signedIn = () => ok({ status: 'ok' })

export const authHandlers = [
  http.get(p('auth/status'), () =>
    ok({ registered: db.registered, registration_open: !db.registered })),
  http.post(p('auth/login'), async ({ request }) => {
    const b = await jsonBody(request)
    if (str(b.username) !== MOCK_USER || str(b.password) !== db.password) {
      return fail(401, 'username หรือ password ไม่ถูกต้อง', 'auth.bad_credentials')
    }
    return signedIn()
  }),
  http.post(p('auth/register'), async ({ request }) => {
    if (db.registered) return fail(403, 'มี user อยู่แล้ว — สมัครซ้ำไม่ได้', 'auth.user_exists')
    const b = await jsonBody(request)
    if (str(b.password).length < PASSWORD_MIN) {
      return fail(400, 'password too short', 'auth.password_short', { min: PASSWORD_MIN })
    }
    db.registered = true
    db.password = str(b.password)
    return signedIn()
  }),
  http.post(p('auth/password'), async ({ request }) => {
    const b = await jsonBody(request)
    const current = str(b.current_password)
    const next = str(b.new_password)
    if (current !== db.password) {
      return fail(403, 'current password is wrong', 'auth.wrong_current_password')
    }
    if (next.length < PASSWORD_MIN) {
      return fail(400, 'password too short', 'auth.password_short', { min: PASSWORD_MIN })
    }
    if (next === current) {
      return fail(400, 'new password equals the current one', 'auth.password_unchanged')
    }
    db.password = next
    return ok({ status: 'ok', token: 'mock-token-after-password-change' })
  }),
  http.post(p('auth/logout'), () => ok({ status: 'ok', revoked: true })),
]
