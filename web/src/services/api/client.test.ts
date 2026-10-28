import { describe, expect, it } from 'vitest'
import { http, HttpResponse } from 'msw'
import * as z from 'zod/mini'
import { server } from '../../testing/mocks/testServer.ts'
import { ApiError, apiGet, shouldRetry } from './client.ts'
import { apiPattern, apiUrl } from './url.ts'

describe('apiUrl', () => {
  it('puts paths under the API base and drops empty query values', () => {
    const url = apiUrl('radar_round/list', { limit: 5, list_name: undefined })
    expect(url.pathname).toBe('/api/radar_round/list')
    expect(url.search).toBe('?limit=5')
  })
})

describe('apiGet', () => {
  const schema = z.array(z.looseObject({ id: z.number() }))

  it('fills path params and parses the body', async () => {
    const rows = await apiGet('history/{history_id}', z.array(z.unknown()), {
      path: { history_id: 42 },
    })
    expect(rows.length).toBeGreaterThan(0)
  })

  it('throws ApiError with the server detail', async () => {
    const err = await apiGet('history/{history_id}', schema, { path: { history_id: 1 } })
      .catch((e: unknown) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).status).toBe(404)
    expect((err as ApiError).detail).toBe('History record not found')
  })

  it('rejects a body that does not match the schema', async () => {
    server.use(http.get(apiPattern('history'), () => HttpResponse.json([{ id: 'x' }])))
    await expect(apiGet('history', schema)).rejects.toThrow()
  })

  it('reports 401 as ApiError', async () => {
    server.use(http.get(apiPattern('version'), () =>
      HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 })))
    await expect(apiGet('version', z.unknown())).rejects.toMatchObject({ status: 401 })
  })
})

describe('shouldRetry', () => {
  it('never retries 4xx, retries 5xx twice', () => {
    expect(shouldRetry(0, new ApiError(404, null))).toBe(false)
    expect(shouldRetry(0, new ApiError(503, null))).toBe(true)
    expect(shouldRetry(2, new ApiError(503, null))).toBe(false)
  })
})
