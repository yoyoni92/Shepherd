// Act-as (WebUI Feature 8): a system admin operating a tenant's company-admin
// console. The state lives in two client-set cookies so both the server (Fleet
// proxy + layout) and the client (nav + banner) can read it:
//   - `act_as_company`: the bare target company_id (the proxy reads only this).
//   - `act_as`: a JSON blob with the company name + feature flags, for the banner
//     label and nav gating (which are company-scoped, not the operator's flags).

export type ActAsState = {
  company_id: string
  name: string
  feature_flags: Record<string, unknown>
}

export const ACT_AS_COMPANY_COOKIE = 'act_as_company'
export const ACT_AS_STATE_COOKIE = 'act_as'

// Parse the JSON `act_as` cookie value (works server- or client-side). Returns
// null when absent or malformed so callers can treat it as "not acting-as".
export function parseActAs(raw: string | undefined | null): ActAsState | null {
  if (!raw) return null
  try {
    const v = JSON.parse(raw)
    if (v && typeof v.company_id === 'string') {
      return {
        company_id: v.company_id,
        name: typeof v.name === 'string' ? v.name : '',
        feature_flags: v.feature_flags && typeof v.feature_flags === 'object' ? v.feature_flags : {},
      }
    }
  } catch {
    /* malformed cookie - treat as not acting-as */
  }
  return null
}

// Client-only: enter act-as by writing both cookies (24h, lax). The caller then
// hard-navigates so every server read (middleware, layout, proxy) re-runs fresh.
export function setActAsCookies(state: ActAsState): void {
  const opts = 'path=/; max-age=86400; samesite=lax'
  document.cookie = `${ACT_AS_COMPANY_COOKIE}=${encodeURIComponent(state.company_id)}; ${opts}`
  document.cookie = `${ACT_AS_STATE_COOKIE}=${encodeURIComponent(JSON.stringify(state))}; ${opts}`
}

// Client-only: exit act-as by expiring both cookies.
export function clearActAsCookies(): void {
  const opts = 'path=/; max-age=0; samesite=lax'
  document.cookie = `${ACT_AS_COMPANY_COOKIE}=; ${opts}`
  document.cookie = `${ACT_AS_STATE_COOKIE}=; ${opts}`
}
