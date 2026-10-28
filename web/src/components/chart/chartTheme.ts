import { readToken } from '../../stores/theme.ts'

/** Chart colors come from the same CSS tokens as the page (cards sit on --card). */
export function chartColors() {
  return {
    bg: readToken('--card'),
    fg: readToken('--muted-foreground'),
    grid: readToken('--border'),
    up: readToken('--up'),
    down: readToken('--down'),
  }
}
