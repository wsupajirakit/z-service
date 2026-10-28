import { m } from '../../../paraglide/messages.js'
import { PageHeader } from '../../../components/ui/PageHeader.tsx'
import { QueryState } from '../../../components/ui/QueryState.tsx'
import { useJob } from '../api.ts'
import { isRunning } from '../model.ts'
import { AutoStart } from './AutoStart.tsx'
import { CustomRun } from './CustomRun.tsx'
import { JobStatus } from './JobStatus.tsx'
import { SingleFetch } from './SingleFetch.tsx'
import { TvTest } from './TvTest.tsx'

export function JobsPage() {
  const job = useJob()
  const busy = isRunning(job.data)
  return (
    <section className="space-y-6">
      <PageHeader description={m.page_desc_dashboard()} />
      <QueryState query={job}>{(j) => <JobStatus job={j} />}</QueryState>
      <div className="grid gap-6 xl:grid-cols-2">
        <AutoStart busy={busy} />
        <CustomRun busy={busy} />
      </div>
      <TvTest />
      <SingleFetch />
    </section>
  )
}
