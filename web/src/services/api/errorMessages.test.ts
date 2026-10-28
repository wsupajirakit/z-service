import { describe, expect, it } from 'vitest'
import { http, HttpResponse } from 'msw'
import * as z from 'zod/mini'
import en from '../../../messages/en.json'
import { server } from '../../testing/mocks/testServer.ts'
import { ApiError, apiGet } from './client.ts'
import { ERROR_MESSAGES, codeMessage, errorText } from './errorMessages.ts'
import { apiPattern } from './url.ts'

const messageKey = (code: string) => `err_${code.replace('.', '_')}`

// Tests run in the base locale (en).
describe('error codes', () => {
  it('maps every err_* message, and nothing else', () => {
    const keys = Object.keys(en).filter((k) => k.startsWith('err_')).sort()
    expect(Object.keys(ERROR_MESSAGES).map(messageKey).sort()).toEqual(keys)
  })

  it('fills params into the translated text', () => {
    expect(codeMessage('auth.rate_limited', { retry_after: 30 }))
      .toBe('Too many attempts — wait 30 seconds')
    expect(codeMessage('nope.unknown', {})).toBeNull()
    expect(codeMessage(null, {})).toBeNull()
  })

  it('reads code and params from the answer; unknown codes fall back to detail', async () => {
    server.use(http.get(apiPattern('history'), () => HttpResponse.json(
      { detail: 'hours must be between 1 and 720.', code: 'history.hours_range',
        params: { min: 1, max: 720, nested: { no: 1 } } },
      { status: 400 },
    )))
    const err = await apiGet('history', z.unknown()).catch((e: unknown) => e) as ApiError
    expect(err.code).toBe('history.hours_range')
    expect(err.params).toEqual({ min: 1, max: 720 })
    expect(errorText(err)).toBe('Hours must be between 1 and 720')
    expect(errorText(new ApiError(409, 'busy', 'future.code'))).toBe('Server answered 409 busy')
    expect(errorText(new ApiError(500, 'plain'))).toBe('Server answered 500 plain')
  })
})
