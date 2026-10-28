// Starts the mock API in the browser. Imported only when MODE === 'mock'.
import { setupWorker } from 'msw/browser'
import { handlers } from './handlers.ts'

export async function startMocks(): Promise<void> {
  const worker = setupWorker(...handlers)
  await worker.start({
    serviceWorker: { url: `${import.meta.env.BASE_URL}mockServiceWorker.js` },
  })
}
