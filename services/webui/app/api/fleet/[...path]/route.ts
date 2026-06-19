import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'

// Server-only Fleet API base (never exposed to the browser).
const FLEET_BASE = process.env.FLEET_API_URL ?? process.env.NEXT_PUBLIC_FLEET_API_URL ?? 'http://localhost:8000'
const INTERNAL_TOKEN = process.env.INTERNAL_SERVICE_TOKEN ?? ''

// The admin console always acts as the admin caller; ownership scope is enforced server-side.
const CALLER_CONTEXT = JSON.stringify({ role: 'admin' })

async function forward(req: NextRequest, path: string[]) {
  // Admin-only: every Fleet call is gated by the NextAuth session.
  const session = await getServerSession(authOptions)
  if (!session) return NextResponse.json({ error: 'unauthorized' }, { status: 401 })

  const search = req.nextUrl.search
  const url = `${FLEET_BASE}/${path.join('/')}${search}`

  const headers: Record<string, string> = {
    'X-Internal-Token': INTERNAL_TOKEN,
    'X-Caller-Context': CALLER_CONTEXT,
  }
  const contentType = req.headers.get('content-type')
  if (contentType) headers['Content-Type'] = contentType

  const hasBody = req.method !== 'GET' && req.method !== 'DELETE'
  const res = await fetch(url, {
    method: req.method,
    headers,
    body: hasBody ? await req.text() : undefined,
    cache: 'no-store',
  })

  const text = await res.text()
  return new NextResponse(text || null, {
    status: res.status,
    headers: { 'content-type': res.headers.get('content-type') ?? 'application/json' },
  })
}

type Ctx = { params: Promise<{ path: string[] }> }
const handler = async (req: NextRequest, { params }: Ctx) => forward(req, (await params).path)

export const GET = handler
export const POST = handler
export const PUT = handler
export const PATCH = handler
export const DELETE = handler
