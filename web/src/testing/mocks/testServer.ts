// Vitest setup: every fetch in tests goes to the MSW handlers; unknown requests fail the test.
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { resetDb } from './db.ts'
import { handlers } from './handlers.ts'

export const server = setupServer(...handlers)

beforeAll(() => server.listen({ onUnhandledFrame: 'error' }))
afterEach(() => {
  server.resetHandlers()
  resetDb()
})
afterAll(() => server.close())
