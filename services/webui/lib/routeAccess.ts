// Central route -> allowedRoles gate. Everything is allowed to a system admin;
// company_admin is denied the system-only areas (company/user management + ops).
// Anything not listed here is allowed to both roles (company-scoped server-side).

const ROUTE_ROLES: { prefix: string; roles: string[] }[] = [
  { prefix: '/companies', roles: ['admin'] },
  { prefix: '/access', roles: ['admin'] },
  { prefix: '/health', roles: ['admin'] },
  { prefix: '/config', roles: ['admin'] },
  { prefix: '/bot', roles: ['admin'] },
]

export function isRouteAllowed(pathname: string, role: string): boolean {
  const rule = ROUTE_ROLES.find((r) => pathname === r.prefix || pathname.startsWith(r.prefix + '/'))
  return rule ? rule.roles.includes(role) : true
}
