import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { postImpersonationAudit, type AuditAction } from '@/lib/audit'

// Client-facing audit route for act-as start/stop (Feature 8). Only a system-admin
// session may use it; it forwards to fleet-api with a company-less system-admin
// caller carrying the operator (see lib/audit). Best-effort: never faults the UI.
export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session || session.user.role !== 'admin') {
    return NextResponse.json({ error: 'forbidden' }, { status: 403 })
  }

  let payload: { company_id?: string; action?: AuditAction; detail?: string }
  try {
    payload = await req.json()
  } catch {
    return NextResponse.json({ error: 'bad request' }, { status: 400 })
  }
  const { company_id, action, detail } = payload
  if (!company_id || (action !== 'start' && action !== 'stop' && action !== 'write')) {
    return NextResponse.json({ error: 'bad request' }, { status: 400 })
  }

  try {
    await postImpersonationAudit({ operatorId: session.user.id, companyId: company_id, action, detail })
  } catch {
    /* best-effort - the act-as session is not blocked by an audit failure */
  }
  return NextResponse.json({ status: 'ok' })
}
