// Builds the `X-Caller-Context` the Fleet proxy injects, from the session role.
// company_admin is always locked to its own company_id; a system admin is scoped
// to the active company chosen in the switcher (cookie), or cross-company when none.

export type CallerUser = { role: string; company_id: string | null }

export function buildCallerContext(user: CallerUser, activeCompanyId?: string): string {
  if (user.role === 'company_admin') {
    return JSON.stringify({ role: 'company_admin', company_id: user.company_id })
  }
  // System admin: company_id only when an explicit company is selected.
  const ctx: { role: string; company_id?: string } = { role: 'admin' }
  if (activeCompanyId && activeCompanyId !== 'all') ctx.company_id = activeCompanyId
  return JSON.stringify(ctx)
}
