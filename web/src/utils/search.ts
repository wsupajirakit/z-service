// Search-param validators for route `validateSearch`. Route configs are part of the entry chunk,
// so these are plain functions: zod/mini would pull ~7 KB gzip into the first load.
type Raw = Record<string, unknown>

/** An integer (number or numeric string); anything else is dropped. */
export function searchInt(raw: Raw, key: string): number | undefined {
  const value = raw[key]
  const n = typeof value === 'number' ? value : typeof value === 'string' ? Number(value) : NaN
  return Number.isSafeInteger(n) && (typeof value !== 'string' || value.trim() !== '')
    ? n
    : undefined
}

/** A non-empty string; anything else is dropped. Numbers are kept as their string form. */
export function searchText(raw: Raw, key: string): string | undefined {
  const value = raw[key]
  if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  return typeof value === 'string' && value.length > 0 ? value : undefined
}

/** Drops undefined values so the URL stays clean. */
export function compact<T extends Raw>(values: T): Partial<T> {
  return Object.fromEntries(Object.entries(values).filter(([, v]) => v !== undefined)) as Partial<T>
}
