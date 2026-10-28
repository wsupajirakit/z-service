import { describe, expect, it } from 'vitest'
import { m } from '../paraglide/messages.js'

// Plurals come from Intl.PluralRules through the message variants (plan §7.1), never from
// string concatenation. Thai has no plural forms, so its single text is used for every count.
describe('plurals', () => {
  it('English and Italian pick one/other by the number', () => {
    expect(m.earning_scan_done({ count: 1 }, { locale: 'en' })).toBe('1 symbol scanned')
    expect(m.earning_scan_done({ count: 2 }, { locale: 'en' })).toBe('2 symbols scanned')
    expect(m.earning_scan_done({ count: 0 }, { locale: 'en' })).toBe('0 symbols scanned')
    expect(m.earning_scan_done({ count: 1 }, { locale: 'it' })).toBe('1 simbolo analizzato')
    expect(m.earning_scan_done({ count: 5 }, { locale: 'it' })).toBe('5 simboli analizzati')
  })

  it('server params that arrive as strings still select the right form', () => {
    expect(m.msg_tv_probe_ok({ target: 'X', bars: '1', seconds: '0.4' }, { locale: 'en' }))
      .toBe('X: 1 bar in 0.4 s')
    expect(m.msg_tv_probe_ok({ target: 'X', bars: '50', seconds: '0.4' }, { locale: 'en' }))
      .toBe('X: 50 bars in 0.4 s')
  })

  it('Thai keeps one text for every count', () => {
    expect(m.earning_scan_done({ count: 1 }, { locale: 'th' }))
      .toBe(m.earning_scan_done({ count: 9 }, { locale: 'th' }).replace('9', '1'))
  })
})
