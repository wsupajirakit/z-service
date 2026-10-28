import { defineAction } from '../../services/api/action.ts'
import { apiSend } from '../../services/api/client.ts'
import { statusSchema } from '../../services/api/common.ts'

const touched = [['history']] as const

/** Deletes rows older than `hours`, always keeping the newest row per symbol/interval. */
export const cleanupAction = defineAction((hours: number) =>
  apiSend('post', 'history/cleanup', statusSchema, { query: { hours } }), touched)

/** Deletes every fetch history row. */
export const clearAllAction = defineAction<void, { message?: string }>(() =>
  apiSend('delete', 'history', statusSchema), touched)
