// Typed client on native fetch. Paths, params and request bodies come from the generated
// OpenAPI types; every response is parsed by a zod/mini schema at this boundary.
import type * as z from 'zod/mini'
import { onUnauthorized } from '../auth/session.ts'
import { csrfHeaders } from './csrf.ts'
import type { paths } from './openapi.gen.ts'
import { ApiError, type ErrorParams } from './error.ts'
import { apiUrl } from './url.ts'

export { ApiError, shouldRetry } from './error.ts'

type Strip<P> = P extends `/api/${infer Rest}` ? Rest : never
type GetPaths = { [P in keyof paths]: paths[P] extends { get: object } ? P : never }[keyof paths]
/** API paths relative to the API base, e.g. 'watchlist' or 'history/{history_id}'. */
export type ApiGetPath = Strip<GetPaths>
type Op<P extends ApiGetPath> = paths[`/api/${P}`] extends { get: infer O } ? O : never
type Params<P extends ApiGetPath> = Op<P> extends { parameters: infer R } ? R : never
type PathParams<P extends ApiGetPath> = Params<P> extends { path: infer X } ? X : never
type QueryParams<P extends ApiGetPath> = Params<P> extends { query?: infer X } ? X : never

export type GetOptions<P extends ApiGetPath> = {
  path?: PathParams<P> extends never ? never : PathParams<P>
  query?: QueryParams<P>
  signal?: AbortSignal
}


function fillPath(template: string, params: object | undefined): string {
  const values = (params ?? {}) as Record<string, unknown>
  return template.replace(/\{(\w+)\}/g, (_, key: string) => {
    const value = values[key]
    if (value === undefined || value === null) throw new Error(`missing path param ${key}`)
    return encodeURIComponent(String(value))
  })
}

type ErrorBody = { detail: string | null, code: string | null, params: ErrorParams }

function readParams(value: unknown): ErrorParams {
  if (!value || typeof value !== 'object') return {}
  const out: Record<string, string | number> = {}
  for (const [key, v] of Object.entries(value)) {
    if (typeof v === 'string' || typeof v === 'number') out[key] = v
  }
  return out
}

async function readError(res: Response): Promise<ErrorBody> {
  const empty: ErrorBody = { detail: null, code: null, params: {} }
  let body: unknown
  try {
    body = await res.json()
  } catch {
    return empty // not JSON: nothing to show but the status
  }
  if (!body || typeof body !== 'object') return empty
  const raw = body as { detail?: unknown, code?: unknown, params?: unknown }
  const detail = raw.detail === undefined ? null
    : typeof raw.detail === 'string' ? raw.detail : JSON.stringify(raw.detail)
  const code = typeof raw.code === 'string' ? raw.code : null
  return { detail, code, params: readParams(raw.params) }
}

async function parseResponse<S extends z.ZodMiniType>(res: Response, schema: S) {
  if (res.status === 401) onUnauthorized()
  if (!res.ok) {
    const { detail, code, params } = await readError(res)
    throw new ApiError(res.status, detail, code, params)
  }
  return schema.parse(await res.json()) as z.infer<S>
}

export async function apiGet<P extends ApiGetPath, S extends z.ZodMiniType>(
  path: P,
  schema: S,
  options: GetOptions<P> = {},
): Promise<z.infer<S>> {
  const filled = fillPath(path, options.path as object | undefined)
  const url = apiUrl(filled, options.query as Record<string, unknown>)
  const res = await fetch(url, {
    credentials: 'include',
    headers: { Accept: 'application/json' },
    signal: options.signal,
  })
  return parseResponse(res, schema)
}

export type SendMethod = 'post' | 'put' | 'delete'
type MethodPaths<M extends SendMethod> = {
  [P in keyof paths]: paths[P] extends { [K in M]: object } ? P : never
}[keyof paths]
/** Paths relative to the API base that accept the given write method. */
export type ApiSendPath<M extends SendMethod> = Strip<MethodPaths<M>>
type SendOp<M extends SendMethod, P extends ApiSendPath<M>> =
  paths[`/api/${P}`] extends { [K in M]: infer O } ? O : never
type SendParams<M extends SendMethod, P extends ApiSendPath<M>> =
  SendOp<M, P> extends { parameters: infer R } ? R : never
type SendBody<M extends SendMethod, P extends ApiSendPath<M>> =
  SendOp<M, P> extends { requestBody: { content: { 'application/json': infer B } } } ? B : never

export type SendOptions<M extends SendMethod, P extends ApiSendPath<M>> = {
  path?: SendParams<M, P> extends { path: infer X } ? X : never
  query?: SendParams<M, P> extends { query?: infer X } ? X : never
  body?: SendBody<M, P>
  signal?: AbortSignal
}

/** POST/PUT/DELETE with a JSON body; sends the CSRF header when the cookie exists. */
export async function apiSend<M extends SendMethod, P extends ApiSendPath<M>,
  S extends z.ZodMiniType>(
  method: M,
  path: P,
  schema: S,
  options: SendOptions<M, P> = {},
): Promise<z.infer<S>> {
  const filled = fillPath(path, options.path as object | undefined)
  const url = apiUrl(filled, options.query as Record<string, unknown>)
  const hasBody = options.body !== undefined
  const res = await fetch(url, {
    method: method.toUpperCase(),
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      ...(hasBody ? { 'Content-Type': 'application/json' } : {}),
      ...csrfHeaders(),
    },
    body: hasBody ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
  })
  return parseResponse(res, schema)
}
