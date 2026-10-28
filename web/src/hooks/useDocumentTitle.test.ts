import { describe, expect, it } from 'vitest'
import { m } from '../paraglide/messages.js'
import { pageTitle } from './useDocumentTitle.ts'

describe('document title', () => {
  it('is the translated page name plus the app name, or the app name alone', () => {
    expect(pageTitle('nav_settings')).toBe(`${m.nav_settings()} · ${m.app_title()}`)
    expect(pageTitle(undefined)).toBe(m.app_title())
  })
})
