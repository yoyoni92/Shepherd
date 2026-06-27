// Builds the `X-Caller-Context` the Fleet proxy injects, from the session role.
// company_admin is always locked to its own company_id; a system admin is scoped
// to the active company chosen in the switcher (cookie), or cross-company when none.

export type CallerUser = { role: string; company_id: string | null }

// Optional act-as: a system admin operating a tenant's company-admin console. The
// target company id + the operator's user id (carried as `impersonator`, exactly
// like F6/the bot) are only honored when the session role is `admin`.
export type ActAs = { companyId: string; operatorId: string }

export function buildCallerContext(user: CallerUser, activeCompanyId?: string, actAs?: ActAs): string {
  // Act-as overrides the normal admin/switcher logic: forge a company_admin context
  // scoped to the target company, tagged with the operator as the impersonator.
  if (actAs && user.role === 'admin') {
    return JSON.stringify({
      role: 'company_admin',
      company_id: actAs.companyId,
      impersonator: actAs.operatorId,
    })
  }
  if (user.role === 'company_admin') {
    return JSON.stringify({ role: 'company_admin', company_id: user.company_id })
  }
  // System admin: company_id only when an explicit company is selected.
  const ctx: { role: string; company_id?: string } = { role: 'admin' }
  if (activeCompanyId && activeCompanyId !== 'all') ctx.company_id = activeCompanyId
  return JSON.stringify(ctx)
}
