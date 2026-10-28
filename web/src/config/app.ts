// App-wide tunables. Poll intervals, cache lifetimes and URLs live here, never in components.
export const appConfig = {
  /** How long fetched data counts as fresh, per kind of data (ms). */
  staleTime: {
    /** Settings, version, symbol list: change rarely. */
    static: 5 * 60_000,
    /** Browsable lists (watchlist, history, rounds). */
    list: 30_000,
    /** Job status while something may be running. */
    status: 5_000,
  },
  /** Poll intervals (ms). Only used while the tab is visible (TanStack Query default). */
  poll: {
    radarStatus: 5_000,
    /** /automate/status: fast while a job runs, slow otherwise (cooldown, idle). */
    jobRunning: 3_000,
    jobIdle: 20_000,
    goldRunning: 3_000,
  },
  /** Page sizes passed as `limit` to list endpoints. */
  pageSize: {
    radarRounds: 30,
    stockRadarHistory: 50,
    earningScanHistory: 50,
  },
  /** Table pagination: page-size choices and the default. */
  table: { pageSizes: [10, 25, 50, 100], pageSize: 25 },
} as const
