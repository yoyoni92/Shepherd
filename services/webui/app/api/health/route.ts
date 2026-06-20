import { NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import type { ServiceHealth } from '@/lib/health'

// Server-only base URLs; every service exposes GET /health. fleet-api's /health is unauthenticated.
const SERVICES: { key: string; url: string | undefined }[] = [
  { key: 'fleet', url: process.env.FLEET_API_URL ?? process.env.NEXT_PUBLIC_FLEET_API_URL },
  { key: 'agent', url: process.env.AGENT_URL },
  { key: 'rag', url: process.env.RAG_URL },
  { key: 'gateway', url: process.env.GATEWAY_URL },
  { key: 'assistant', url: process.env.ASSISTANT_URL },
]

// ponytail: fixed 3s probe timeout — bump if a service is legitimately slow to answer /health
const TIMEOUT_MS = 3000

async function ping(url: string | undefined): Promise<Omit<ServiceHealth, 'key'>> {
  if (!url) return { status: 'down', latencyMs: null }
  const started = Date.now()
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS)
  try {
    const res = await fetch(`${url}/health`, { signal: ctrl.signal, cache: 'no-store' })
    return { status: res.ok ? 'up' : 'down', latencyMs: Date.now() - started }
  } catch {
    return { status: 'down', latencyMs: null }
  } finally {
    clearTimeout(timer)
  }
}

export async function GET() {
  const session = await getServerSession(authOptions)
  if (!session) return NextResponse.json({ error: 'unauthorized' }, { status: 401 })

  const services: ServiceHealth[] = await Promise.all(
    SERVICES.map(async (s) => ({ key: s.key, ...(await ping(s.url)) })),
  )
  return NextResponse.json({ services, checkedAt: new Date().toISOString() })
}
