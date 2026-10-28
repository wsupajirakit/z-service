import { describe, expect, it } from 'vitest'
import { appEnv, parseBasePath } from './env.ts'

describe('appEnv', () => {
  it('parses base paths that start and end with a slash', () => {
    expect(appEnv.appBase.startsWith('/')).toBe(true)
    expect(appEnv.appBase.endsWith('/')).toBe(true)
    expect(appEnv.apiBase.endsWith('/')).toBe(true)
  })

  it('rejects paths without slashes, upper case or non-strings', () => {
    expect(() => parseBasePath('x', 'app/')).toThrow()
    expect(() => parseBasePath('x', '/app')).toThrow()
    expect(() => parseBasePath('x', '/App/')).toThrow()
    expect(() => parseBasePath('x', 42)).toThrow()
    expect(parseBasePath('x', '/a/b-1/')).toBe('/a/b-1/')
  })
})
