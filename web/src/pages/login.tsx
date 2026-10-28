import { createFileRoute } from '@tanstack/react-router'
import { withLocale } from '../i18n/withLocale.tsx'
import { LoginPage } from '../features/auth/index.ts'

// Public: no nav entry, rendered without the signed-in header (see __root.tsx).
export const Route = createFileRoute('/login')({
  staticData: { public: true },
  component: withLocale(LoginPage),
})
