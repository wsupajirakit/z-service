import { createRouter } from '@tanstack/react-router'
import { routeTree } from './routeTree.gen.ts'
import { appEnv } from '../config/env.ts'
import './routeMeta.ts'

export const router = createRouter({
  routeTree,
  basepath: appEnv.appBase,
  // Starlette StaticFiles redirects /app/watchlist -> /app/watchlist/, so links match that form.
  trailingSlash: 'always',
  defaultPreload: 'intent',
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
