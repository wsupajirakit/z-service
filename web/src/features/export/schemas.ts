import * as z from 'zod/mini'

// GET /api/export/check?interval&list_name
export const exportCheckSchema = z.looseObject({
  total_in_list: z.number(),
  available_count: z.number(),
  missing_count: z.number(),
  missing_symbols: z.array(z.string()),
})
export type ExportCheck = z.infer<typeof exportCheckSchema>
