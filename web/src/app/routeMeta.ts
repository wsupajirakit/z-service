import type { TitleKey } from '../i18n/messageKey.ts'

declare module '@tanstack/react-router' {
  interface StaticDataRouteOption {
    /** Message key for the nav label and page title. */
    titleKey?: TitleKey
    /** Nav order; lower comes first. */
    navOrder?: number
    /** Reachable without a session (the sign-in page): no nav, no sign-out. */
    public?: boolean
  }
}

export {}
