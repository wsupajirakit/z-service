// Runs synchronously in <head> before first paint so the page never flashes the wrong theme.
// Kept as an external file so CSP script-src 'self' needs no inline script. The choice lives
// in the zs_theme cookie (written by src/stores/theme.ts); without it the theme is dark.
(function () {
  let theme = 'dark'
  try {
    const hit = /(?:^|;\s*)zs_theme=(light|dark)(?:;|$)/.exec(document.cookie)
    if (hit) theme = hit[1]
  } catch {
    // cookies unreadable: keep the default
  }
  document.documentElement.dataset.theme = theme
})()
