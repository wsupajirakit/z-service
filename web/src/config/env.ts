// Runtime config, validated once at boot. Values come from the build env, never literals here.
// Plain checks instead of zod: this module is on the first-load path, and zod/mini (~13 KB gzip)
// is only needed by pages that parse API responses, so it stays in lazy chunks.
const BASE_PATH = /^\/(?:[a-z0-9-]+\/)*$/

export type AppEnv = { appBase: string; apiBase: string }

export function parseBasePath(name: string, value: unknown): string {
  if (typeof value !== 'string' || !BASE_PATH.test(value)) {
    throw new Error(`invalid ${name}: expected a path like /app/`)
  }
  return value
}

export const appEnv: AppEnv = {
  appBase: parseBasePath('appBase', import.meta.env.BASE_URL),
  apiBase: parseBasePath('apiBase', __APP_API_BASE__),
}
