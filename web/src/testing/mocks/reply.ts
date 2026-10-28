import { HttpResponse, type JsonBodyType } from 'msw'

export const ok = (body: JsonBodyType) => HttpResponse.json(body)
/** An error answer shaped like the backend's ApiError: detail + code (+ params). 422s
 * (FastAPI validation) carry no code, as on the real server. */
export const fail = (status: number, detail: string, code?: string,
  params?: Record<string, string | number>) =>
  HttpResponse.json({ detail, ...(code ? { code } : {}), ...(params ? { params } : {}) },
    { status })

/** Reads a JSON body as a plain object ({} when absent or not an object). */
export async function jsonBody(request: Request): Promise<Record<string, unknown>> {
  try {
    const body: unknown = await request.json()
    return body && typeof body === 'object' ? (body as Record<string, unknown>) : {}
  } catch {
    return {}
  }
}

export const str = (v: unknown) => (typeof v === 'string' ? v : '')
export const num = (v: unknown) => (typeof v === 'number' ? v : NaN)
export const strList = (v: unknown) =>
  Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : []
