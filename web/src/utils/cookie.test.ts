import { describe, expect, it } from 'vitest'
import { cookieString, readCookie } from './cookie.ts'

describe('preference cookies', () => {
  it('are site-wide, same-site only, kept a year, and Secure only over https', () => {
    expect(cookieString('zs_theme', 'dark', false))
      .toBe('zs_theme=dark; Path=/; Max-Age=31536000; SameSite=Strict')
    expect(cookieString('zs_theme', 'light', true)).toMatch(/; SameSite=Strict; Secure$/)
  })

  it('reads nothing when there is no document', () => {
    expect(readCookie('zs_theme')).toBeNull()
  })
})
