import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { setupAuth } from './auth'

setupAuth()

// After a deploy, a tab opened earlier still names the old build's files; when one of
// them fails to load, reload once to pick up the new build (at most once a minute).
window.addEventListener('vite:preloadError', (event) => {
  const last = Number(sessionStorage.getItem('zs.reloadedAt') || 0)
  if (Date.now() - last < 60_000) return
  event.preventDefault()
  sessionStorage.setItem('zs.reloadedAt', String(Date.now()))
  window.location.reload()
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
