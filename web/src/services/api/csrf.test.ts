import { afterEach, describe, expect, it, vi } from 'vitest'
import { http, HttpResponse } from 'msw'
import * as z from 'zod/mini'
import { server } from '../../testing/mocks/testServer.ts'
import { ApiError, apiSend } from './client.ts'
import { CSRF_HEADER, csrfHeaders, readCookie } from './csrf.ts'
import { apiHref, apiPattern } from './url.ts'

describe('csrf', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('reads the cookie and sends nothing without it', () => {
    expect(readCookie('a=1; __Host-zs_csrf=tok%3D1', '__Host-zs_csrf')).toBe('tok=1')
    expect(readCookie('a=1', '__Host-zs_csrf')).toBeNull()
    expect(csrfHeaders('a=1')).toEqual({})
    expect(csrfHeaders('__Host-zs_csrf=abc')).toEqual({ [CSRF_HEADER]: 'abc' })
  })

  it('apiSend echoes the cookie in X-ZS-CSRF and sends the JSON body', async () => {
    vi.stubGlobal('document', { cookie: 'x=y; __Host-zs_csrf=t0k' })
    let seen: { csrf: string | null; type: string | null; body: unknown } | null = null
    server.use(http.post(apiPattern('settings/tv_mode'), async ({ request }) => {
      seen = {
        csrf: request.headers.get(CSRF_HEADER),
        type: request.headers.get('content-type'),
        body: await request.json(),
      }
      return HttpResponse.json({ mode: 2 })
    }))
    const out = await apiSend('post', 'settings/tv_mode', z.looseObject({ mode: z.number() }), {
      body: { mode: 2 },
    })
    expect(out.mode).toBe(2)
    expect(seen).toEqual({ csrf: 't0k', type: 'application/json', body: { mode: 2 } })
  })

  it('apiSend without the cookie sends no CSRF header; errors carry detail', async () => {
    let header: string | null = 'unset'
    server.use(http.delete(apiPattern('radar_round/:stamp'), ({ request }) => {
      header = request.headers.get(CSRF_HEADER)
      return HttpResponse.json({ detail: 'no round x' }, { status: 404 })
    }))
    const err = await apiSend('delete', 'radar_round/{stamp}', z.unknown(), {
      path: { stamp: 'x' },
    }).catch((e: unknown) => e)
    expect(header).toBeNull()
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).detail).toBe('no round x')
  })

  it('apiHref is a same-origin relative link', () => {
    expect(apiHref('export_zip', { all: true, list_name: undefined }))
      .toBe('/api/export_zip?all=true')
  })
})
