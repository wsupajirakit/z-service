import { useNavigate } from '@tanstack/react-router'
import { m } from '../paraglide/messages.js'
import { logout } from '../services/auth/session.ts'
import { ChevronDownIcon, LogOutIcon, SettingsIcon, UserIcon } from '../components/ui/icons.tsx'
import { Menu } from '../components/ui/Menu.tsx'

/** Account menu: settings and sign-out. */
export function UserMenu() {
  const navigate = useNavigate()
  return (
    <Menu
      testId="user-menu"
      label={m.user_menu()}
      header={m.user_menu_signed_in()}
      trigger={(
        <>
          <span className="grid size-7 place-items-center rounded-full bg-secondary
            text-secondary-foreground">
            <UserIcon size={15} />
          </span>
          <ChevronDownIcon size={14} className="text-muted-foreground" />
        </>
      )}
      items={[
        {
          key: 'settings',
          label: m.nav_settings(),
          icon: <SettingsIcon />,
          onSelect: () => void navigate({ to: '/settings/' }),
        },
        {
          key: 'logout',
          label: m.logout(),
          icon: <LogOutIcon />,
          destructive: true,
          onSelect: () => void logout(),
        },
      ]}
    />
  )
}
