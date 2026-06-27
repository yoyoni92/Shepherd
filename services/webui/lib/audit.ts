// Server-only helper that records an impersonation row on fleet-api, reusing the
// F6 endpoint. The audit caller MUST be a company-LESS system admin carrying the
// operator as `impersonator`: the act-as (company_admin) context would 403 on
// /sysadmin/*, exactly like the bot. Both the Fleet proxy (per-write) and the
// webui audit route (start/stop) call this.

const FLEET_BASE = process.env.FLEET_API_URL ?? process.env.NEXT_PUBLIC_FLEET_API_URL ?? 'http://localhost:8000'
const INTERNAL_TOKEN = process.env.INTERNAL_SERVICE_TOKEN ?? ''

export type AuditAction = 'start' | 'stop' | 'write'

export async function postImpersonationAudit(opts: {
  operatorId: string
  companyId: string
  action: AuditAction
  detail?: string
}): Promise<void> {
  const caller = JSON.stringify({ role: 'admin', impersonator: opts.operatorId })
  const body: Record<string, unknown> = {
    company_id: opts.companyId,
    effective_role: 'company_admin',
    action: opts.action,
  }
  if (opts.detail) body.detail = opts.detail
  await fetch(`${FLEET_BASE}/sysadmin/impersonation-audit`, {
    method: 'POST',
    headers: {
      'X-Internal-Token': INTERNAL_TOKEN,
      'X-Caller-Context': caller,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
    cache: 'no-store',
  })
}
