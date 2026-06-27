import type { DefaultSession } from 'next-auth'
import 'next-auth/jwt'

// The session/JWT carry the app-user identity returned by the fleet-api login
// contract (POST /auth/login): role + tenant scope + the portable JWT.
declare module 'next-auth' {
  interface Session {
    user: {
      id: string
      role: string
      company_id: string | null
      feature_flags: Record<string, unknown>
      token?: string
    } & DefaultSession['user']
  }

  interface User {
    role: string
    company_id: string | null
    feature_flags?: Record<string, unknown>
    token?: string
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    id?: string
    role?: string
    company_id?: string | null
    feature_flags?: Record<string, unknown>
    token?: string
  }
}
