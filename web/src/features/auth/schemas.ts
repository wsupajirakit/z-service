import * as z from 'zod/mini'

// GET /api/auth/status: register is offered only on the first run, when the server allows it.
export const authStatusSchema = z.looseObject({
  registered: z.boolean(),
  registration_open: z.optional(z.boolean()),
})
export type AuthStatus = z.infer<typeof authStatusSchema>

// POST /api/auth/{login,register}: the server sets the HttpOnly session + CSRF cookies.
export const signedInSchema = z.looseObject({ status: z.string() })
