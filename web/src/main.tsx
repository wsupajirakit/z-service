import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from '@tanstack/react-router'
import { QueryClientProvider } from '@tanstack/react-query'
import { router } from './app/router.ts'
import { queryClient } from './app/queryClient.ts'
import { currentLocale } from './stores/locale.ts'
import './styles/index.css'

document.documentElement.lang = currentLocale()

const rootEl = document.getElementById('root')
if (!rootEl) throw new Error('#root missing')

// `npm run dev:mock` serves every API call from MSW; production builds drop this branch.
if (import.meta.env.MODE === 'mock') {
  const { startMocks } = await import('./testing/mocks/browser.ts')
  await startMocks()
}

createRoot(rootEl).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
)

if (import.meta.env.MODE === 'selftest') {
  void import('./app/selftest.ts').then((s) => s.runSelfTest())
}
