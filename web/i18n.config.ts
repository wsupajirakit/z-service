// Paraglide compiler options shared by vite.config.ts and scripts/gen-i18n.ts.
// The language choice lives in the zs_locale cookie only (site-wide, same-site, Secure on
// https, one year); without it the app starts in the base locale, English.
export const paraglideOptions = {
  project: './project.inlang',
  outdir: './src/paraglide',
  strategy: ['cookie', 'baseLocale'],
  cookieName: 'zs_locale',
  cookieMaxAge: 365 * 24 * 60 * 60,
  cookieSameSite: 'strict',
  cookieSecure: 'auto',
  emitTsDeclarations: true,
} as const
