// Reads the route list from the router-plugin output (src/app/routeTree.gen.ts).
// Never typed by hand.
import { readFileSync } from 'node:fs'

export function readFullPaths(file = 'src/app/routeTree.gen.ts'): string[] {
  const src = readFileSync(file, 'utf8')
  // One line for a single route (`fullPaths: '/'`), a `| '/a'` union per line for more.
  const match = src.match(/fullPaths:\s*((?:\|?\s*'[^']*'\s*)+)/)
  if (!match?.[1]) throw new Error(`fullPaths union not found in ${file}`)
  const paths = [...match[1].matchAll(/'([^']*)'/g)].map((m) => m[1] ?? '')
  if (paths.length === 0) throw new Error(`no routes parsed from ${file}`)
  return paths
}
