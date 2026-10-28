// After `vite build`: copy dist/index.html to dist/<route>/index.html for every static route,
// so a deep link or F5 on /<base>/<route>/ is served by Starlette StaticFiles(html=True).
import { copyFileSync, existsSync, mkdirSync } from 'node:fs'
import { join } from 'node:path'
import { readBuildEnv } from '../build-env.ts'
import { readFullPaths } from './route-list.ts'

const dist = 'dist'
const shell = join(dist, 'index.html')
if (!existsSync(shell)) throw new Error('dist/index.html missing: run vite build first')

const { APP_BASE } = readBuildEnv()
const routes = readFullPaths()
const dynamic = routes.filter((p) => p.includes('$'))
if (dynamic.length > 0) {
  throw new Error(`dynamic segments need search params instead: ${dynamic.join(', ')}`)
}

let count = 0
for (const route of routes) {
  const rel = route.replace(/^\/+|\/+$/g, '')
  if (rel === '') continue
  const dir = join(dist, rel)
  mkdirSync(dir, { recursive: true })
  copyFileSync(shell, join(dir, 'index.html'))
  console.log(`shell ${APP_BASE}${rel}/ -> ${join(dir, 'index.html')}`)
  count++
}
console.log(`emit-route-shells: ${count} shells for ${routes.length} routes`)
