'use client'
import { useState } from 'react'
import { UserCog, LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { clearActAsCookies, type ActAsState } from '@/lib/actAs'

// Persistent banner shown while a system admin operates a tenant's company-admin
// console. Exiting records an audit `stop`, clears the act-as cookies, and hard-
// navigates back to /companies so every server/client read resets.
export function ActAsBanner({ actAs }: { actAs: ActAsState }) {
  const [busy, setBusy] = useState(false)

  const exit = async () => {
    setBusy(true)
    try {
      await fetch('/api/impersonation-audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company_id: actAs.company_id, action: 'stop' }),
      })
    } catch {
      /* best-effort - exit regardless */
    }
    clearActAsCookies()
    window.location.assign('/companies')
  }

  return (
    <div
      className="flex items-center gap-3 shrink-0"
      style={{
        padding: '8px 26px',
        background: 'rgba(251,191,36,.12)',
        borderBottom: '1px solid rgba(251,191,36,.35)',
        color: '#fbbf24',
      }}
    >
      <UserCog size={16} />
      <span className="text-[13px] font-bold">
        פועל כמנהל חברה · <span className="font-extrabold">{actAs.name}</span>
      </span>
      <span className="flex-1" />
      <Button variant="secondary" size="sm" onClick={exit} disabled={busy}>
        <LogOut size={14} /> {busy ? 'יוצא…' : 'צא'}
      </Button>
    </div>
  )
}
