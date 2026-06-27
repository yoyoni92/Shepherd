import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { cookies } from 'next/headers'
import { authOptions } from '@/lib/auth'
import { buildCallerContext } from '@/lib/callerContext'
import { postImpersonationAudit } from '@/lib/audit'
import { ACT_AS_COMPANY_COOKIE } from '@/lib/actAs'

// Server-only Fleet API base (never exposed to the browser).
const FLEET_BASE = process.env.FLEET_API_URL ?? process.env.NEXT_PUBLIC_FLEET_API_URL ?? 'http://localhost:8000'
const INTERNAL_TOKEN = process.env.INTERNAL_SERVICE_TOKEN ?? ''

async function forward(req: NextRequest, path: string[]) {
  // Every Fleet call is gated by the NextAuth session.
  const session = await getServerSession(authOptions)
  if (!session) return NextResponse.json({ error: 'unauthorized' }, { status: 401 })

  // Caller context is derived from the session: a company_admin is locked to its own
  // company; a system admin is scoped to the active company chosen in the switcher,
  // OR - while acting-as (Feature 8) - forged into that tenant's company_admin.
  const cookieStore = await cookies()
  const active = cookieStore.get('active_company_id')?.value
  const actAsCompany = cookieStore.get(ACT_AS_COMPANY_COOKIE)?.value
  const acting = session.user.role === 'admin' && !!actAsCompany
  const callerContext = buildCallerContext(
    session.user,
    active,
    acting ? { companyId: actAsCompany as string, operatorId: session.user.id } : undefined,
  )

  // Best-effort per-write audit: every mutating request made while acting-as leaves a
  // `write` row. Fire-and-forget so a failing/slow audit never blocks or faults the call.
  if (acting && (req.method === 'POST' || req.method === 'PATCH' || req.method === 'DELETE')) {
    postImpersonationAudit({
      operatorId: session.user.id,
      companyId: actAsCompany as string,
      action: 'write',
      detail: `${req.method} ${path.join('/')}`,
    }).catch(() => {})
  }

  const search = req.nextUrl.search
  const url = `${FLEET_BASE}/${path.join('/')}${search}`

  const headers: Record<string, string> = {
    'X-Internal-Token': INTERNAL_TOKEN,
    'X-Caller-Context': callerContext,
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
