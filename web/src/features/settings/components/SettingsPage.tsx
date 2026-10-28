import { useId, useState, type ReactNode } from 'react'
import { m } from '../../../paraglide/messages.js'
import { PageHeader } from '../../../components/ui/PageHeader.tsx'
import { Tabs, tabIds } from '../../../components/ui/Tabs.tsx'
import { GeneralSettings } from './GeneralSettings.tsx'
import { PasswordSettings } from './PasswordSettings.tsx'
import { TvSettings } from './TvSettings.tsx'

type Section = 'general' | 'tv' | 'password'

/** Every section stays mounted (inactive ones hidden), so typed input survives a tab switch. */
export function SettingsPage() {
  const [tab, setTab] = useState<Section>('general')
  const idBase = useId()
  const panels: Record<Section, ReactNode> = {
    general: <GeneralSettings />,
    tv: <TvSettings />,
    password: <PasswordSettings />,
  }
  return (
    <section className="max-w-4xl space-y-6">
      <PageHeader description={m.page_desc_settings()} />
      <Tabs
        label={m.nav_settings()}
        idBase={idBase}
        value={tab}
        onChange={setTab}
        items={[
          { value: 'general', label: m.settings_tab_general() },
          { value: 'tv', label: m.settings_tv() },
          { value: 'password', label: m.settings_password() },
        ]}
      />
      {(Object.keys(panels) as Section[]).map((key) => (
        <div key={key} role="tabpanel" id={tabIds(idBase, key).panel}
          aria-labelledby={tabIds(idBase, key).tab} hidden={key !== tab}>
          {panels[key]}
        </div>
      ))}
    </section>
  )
}
