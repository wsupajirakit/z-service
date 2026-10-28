import { describe, expect, it } from 'vitest'
import en from '../../../messages/en.json'
import { enumLabel } from '../../i18n/enums.ts'
import { SERVER_MESSAGES, serverText } from './serverMessages.ts'

const key = (code: string) => `msg_${code.replace('.', '_')}`

// Tests run in the base locale (en).
describe('coded server texts', () => {
  it('maps every msg_* message, and nothing else', () => {
    const keys = Object.keys(en).filter((k) => k.startsWith('msg_')).sort()
    expect(Object.keys(SERVER_MESSAGES).map(key).sort()).toEqual(keys)
  })

  it('translates with params, falls back to the server text for unknown codes', () => {
    expect(serverText({ code: 'radar.tf_mixed', params: { tf: '1D', count: 3 }, text: 'x' }))
      .toBe(en.msg_radar_tf_mixed.replace('{tf}', '1D').replace('{count}', '3'))
    expect(serverText({ code: 'future.code', text: 'raw server text' })).toBe('raw server text')
    expect(serverText({ text: 'only text' })).toBe('only text')
    expect(serverText({})).toBe('')
  })

  it('labels server enums, showing unknown values as sent', () => {
    expect(enumLabel('status', 'running')).toBe(en.enum_status_running)
    expect(enumLabel('phase', 'brand-new-phase')).toBe('brand-new-phase')
    expect(enumLabel('mode', null)).toBe('-')
  })
})
