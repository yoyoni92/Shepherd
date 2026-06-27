import type { NextAuthOptions } from 'next-auth'
import CredentialsProvider from 'next-auth/providers/credentials'

// Server-only Fleet API base + internal token (mirrors app/api/fleet/[...path]).
const FLEET_BASE = process.env.FLEET_API_URL ?? process.env.NEXT_PUBLIC_FLEET_API_URL ?? 'http://localhost:8000'
const INTERNAL_TOKEN = process.env.INTERNAL_SERVICE_TOKEN ?? ''

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      // next-auth wraps the channel-agnostic POST /auth/login; it does not own identity.
      async authorize(credentials) {
        const email = credentials?.email
        const password = credentials?.password
        if (!email || !password) return null
        const res = await fetch(`${FLEET_BASE}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Internal-Token': INTERNAL_TOKEN },
          body: JSON.stringify({ email, password }),
          cache: 'no-store',
        })
        if (!res.ok) return null
        const { user, token, feature_flags } = await res.json()
        return {
          id: user.user_id,
          email: user.email,
          name: user.name ?? user.email,
          role: user.role,
          company_id: user.company_id ?? null,
          feature_flags: feature_flags ?? {},
          token,
        }
      },
    }),
  ],
  callbacks: {
    jwt({ token, user }) {
      if (user) {
        token.id = user.id
        token.role = user.role
        token.company_id = user.company_id
        token.feature_flags = user.feature_flags
        token.token = user.token
      }
      return token
    },
    session({ session, token }) {
      if (session.user) {
        session.user.id = token.id as string
        session.user.role = token.role as string
        session.user.company_id = (token.company_id ?? null) as string | null
        session.user.feature_flags = (token.feature_flags ?? {}) as Record<string, unknown>
        session.user.token = token.token as string | undefined
      }
      return session
    },
  },
  pages: { signIn: '/' },
}
