'use client'
import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { Plus, Settings, FolderOpen, KeyRound, UserCog, TriangleAlert } from 'lucide-react'
import { useCompanies } from '@/hooks/useCompanies'
import { useCompanySettings } from '@/hooks/useCompanySettings'
import { fetchCompanySettings } from '@/lib/api/fleet'
import { setActAsCookies } from '@/lib/actAs'
import type { CompanyRead, CompanySettingsUpdate } from '@/lib/api/schemas'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogTitle, DialogClose } from '@/components/ui/dialog'
import { fmtDate } from '@/lib/domain'

const fieldStyle = {
  background: 'var(--panel-2, #0f172a)',
  color: 'var(--muted)',
  border: '1px solid var(--line)',
} as const

function AddCompanyDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { add } = useCompanies()
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const close = () => {
    setName('')
    setErr(null)
    onClose()
  }

  const submit = async () => {
    setErr(null)
    if (!name.trim()) {
      setErr('יש להזין שם חברה')
      return
    }
    setBusy(true)
    try {
      await add({ name: name.trim() })
      close()
    } catch {
      setErr('יצירת החברה נכשלה')
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && close()}>
      <DialogContent style={{ maxWidth: 440 }}>
        <div className="p-6 flex flex-col gap-4">
          <DialogTitle className="text-[16px] font-bold">הוספת חברה</DialogTitle>
          <div className="flex flex-col gap-2">
            <label className="text-[12px] font-semibold text-faint">שם חברה</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="text-[13px] rounded-md px-2 py-2"
              style={fieldStyle}
            />
          </div>
          {err && <p className="text-[12px]" style={{ color: '#f87171' }}>{err}</p>}
          <div className="flex gap-2 justify-end mt-2">
            <DialogClose asChild>
              <Button variant="secondary" size="sm" onClick={close}>
                ביטול
              </Button>
            </DialogClose>
            <Button size="sm" disabled={busy} onClick={submit}>
              {busy ? 'יוצר…' : 'הוסף חברה'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// Per-company attendance enable: writes feature_flags.attendance via the existing
// /companies/{id}/settings. Lazily fetches the company's settings for its current state.
function AttendanceToggle({ companyId }: { companyId: string }) {
  const { settings, save } = useCompanySettings(companyId)
  const [busy, setBusy] = useState(false)
  const ready = !!settings
  const on = settings?.feature_flags?.attendance === true

  const toggle = async () => {
    if (!settings) return
    setBusy(true)
    try {
      await save({ feature_flags: { ...settings.feature_flags, attendance: !on } })
    } finally {
      setBusy(false)
    }
  }

  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label="נוכחות"
      disabled={!ready || busy}
      onClick={toggle}
      className="relative inline-flex items-center rounded-full transition-colors"
      style={{
        width: 38,
        height: 22,
        background: on ? 'rgba(59,130,246,.9)' : 'var(--panel-2, #0f172a)',
        border: '1px solid var(--line)',
        cursor: ready && !busy ? 'pointer' : 'default',
        opacity: ready ? 1 : 0.5,
      }}
    >
      <span
        className="absolute rounded-full transition-all"
        style={{
          width: 14,
          height: 14,
          top: 3,
          // RTL: the knob slides toward the start (right) when on.
          right: on ? 3 : 19,
          background: on ? '#fff' : 'var(--muted)',
        }}
      />
    </button>
  )
}

function CompanySettingsDialog({ company, onClose }: { company: CompanyRead | null; onClose: () => void }) {
  const { settings, save } = useCompanySettings(company?.company_id ?? null)
  const [folderId, setFolderId] = useState('')
  const [creds, setCreds] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [ok, setOk] = useState(false)

  // Reset transient status only when the dialog opens for a (different) company -
  // NOT on every settings refetch, or the post-save refetch would wipe the "saved ✓".
  useEffect(() => {
    setOk(false)
    setErr(null)
  }, [company?.company_id])

  // Hydrate the form when the settings load. The credentials blob is never returned,
  // so the textarea starts empty and is only sent when the admin pastes a new value.
  useEffect(() => {
    if (!settings) return
    setFolderId(settings.gdrive_folder_id ?? '')
    setCreds('')
  }, [settings])

  const submit = async () => {
    setErr(null)
    setOk(false)
    setBusy(true)
    const patch: CompanySettingsUpdate = {
      gdrive_folder_id: folderId.trim() || null,
    }
    if (creds.trim()) patch.gdrive_credentials_json = creds.trim()
    try {
      await save(patch)
      setCreds('')
      setOk(true)
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'שמירת ההגדרות נכשלה')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={!!company} onOpenChange={(v) => !v && onClose()}>
      <DialogContent style={{ maxWidth: 500 }}>
        <div className="p-6 flex flex-col gap-5">
          <div className="flex flex-col gap-1">
            <DialogTitle className="text-[16px] font-bold">הגדרות חברה · {company?.name}</DialogTitle>
            <p className="text-[12px] text-faint">חיבור Google Drive לאחסון מסמכים שהבוט מעלה.</p>
          </div>

          <section className="flex flex-col gap-4 rounded-lg" style={{ ...fieldStyle, padding: 16 }}>
            <div className="flex items-center gap-2 text-[13px] font-bold">
              <FolderOpen size={15} style={{ color: 'var(--accent, #60a5fa)' }} />
              <span>Google Drive</span>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-[12px] font-semibold text-faint">מזהה תיקייה (Folder ID)</label>
              <input
                value={folderId}
                onChange={(e) => setFolderId(e.target.value)}
                dir="ltr"
                placeholder="1A2b3C..."
                className="text-[13px] rounded-md px-2 py-2"
                style={{ ...fieldStyle, background: 'var(--bg, #0b1220)' }}
              />
              <p className="text-[11px] text-faint">המזהה מכתובת התיקייה ב-Drive (אחרי ‎/folders/‎).</p>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="flex items-center gap-2 text-[12px] font-semibold text-faint">
                <KeyRound size={13} />
                <span>פרטי חשבון שירות (JSON)</span>
                {settings?.gdrive_configured && (
                  <span
                    className="text-[11px] font-bold rounded-full px-2 py-0.5"
                    style={{ color: '#86efac', background: 'rgba(134,239,172,.12)' }}
                  >
                    מוגדר ✓
                  </span>
                )}
              </label>
              <textarea
                value={creds}
                onChange={(e) => setCreds(e.target.value)}
                rows={4}
                dir="ltr"
                placeholder={settings?.gdrive_configured ? 'הדבק/י JSON חדש כדי להחליף' : 'הדבק/י את ה-JSON'}
                className="text-[12px] rounded-md px-2 py-2 font-mono"
                style={{ ...fieldStyle, background: 'var(--bg, #0b1220)' }}
              />
              <p className="text-[11px] text-faint">נשמר באופן מאובטח ואינו מוצג שוב לאחר השמירה.</p>
            </div>
          </section>

          {err && <p className="text-[12px]" style={{ color: '#f87171' }}>{err}</p>}
          {ok && <p className="text-[12px]" style={{ color: '#86efac' }}>ההגדרות נשמרו ✓</p>}

          <div className="flex gap-2 justify-end">
            <DialogClose asChild>
              <Button variant="secondary" size="sm" onClick={onClose}>
                סגור
              </Button>
            </DialogClose>
            <Button size="sm" disabled={busy} onClick={submit}>
              {busy ? 'שומר…' : 'שמירה'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// One-time acknowledgement before a system admin enters a tenant's company-admin
// console. Confirming fetches the company's feature flags, sets the act-as cookies,
// records an audit `start`, then hard-navigates to /dashboard as that company admin.
function ActAsDialog({ company, onClose }: { company: CompanyRead | null; onClose: () => void }) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const enter = async () => {
    if (!company) return
    setErr(null)
    setBusy(true)
    try {
      const settings = await fetchCompanySettings(company.company_id)
      setActAsCookies({
        company_id: company.company_id,
        name: company.name,
        feature_flags: settings.feature_flags ?? {},
      })
      try {
        await fetch('/api/impersonation-audit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ company_id: company.company_id, action: 'start' }),
        })
      } catch {
        /* best-effort - entering is not blocked by an audit failure */
      }
      window.location.assign('/dashboard')
    } catch {
      setErr('כניסה לחברה נכשלה')
      setBusy(false)
    }
  }

  return (
    <Dialog open={!!company} onOpenChange={(v) => !v && onClose()}>
      <DialogContent style={{ maxWidth: 440 }}>
        <div className="p-6 flex flex-col gap-4">
          <DialogTitle className="text-[16px] font-bold flex items-center gap-2">
            <UserCog size={17} style={{ color: '#fbbf24' }} />
            כניסה כמנהל חברה · {company?.name}
          </DialogTitle>
          <div
            className="flex items-start gap-2.5 rounded-lg text-[12.5px]"
            style={{ padding: 12, background: 'rgba(251,191,36,.1)', border: '1px solid rgba(251,191,36,.3)', color: '#fbbf24' }}
          >
            <TriangleAlert size={15} className="mt-0.5 shrink-0" />
            <span>
              הפעולות אמיתיות - כל שינוי שתבצע/י יחול על נתוני החברה ויירשם ביומן הביקורת.
            </span>
          </div>
          {err && <p className="text-[12px]" style={{ color: '#f87171' }}>{err}</p>}
          <div className="flex gap-2 justify-end mt-1">
            <DialogClose asChild>
              <Button variant="secondary" size="sm" onClick={onClose} disabled={busy}>
                ביטול
              </Button>
            </DialogClose>
            <Button size="sm" disabled={busy} onClick={enter}>
              {busy ? 'נכנס…' : 'כניסה'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function CompanyRow({ company, canActAs, onSettings, onActAs, onToggle, onDelete }: { company: CompanyRead; canActAs: boolean; onSettings: () => void; onActAs: () => void; onToggle: () => void; onDelete: () => void }) {
  return (
    <tr style={{ borderBottom: '1px solid var(--line)' }}>
      <td style={{ padding: '10px 16px' }} className="font-bold">{company.name}</td>
      <td style={{ padding: '10px 16px' }}>
        <Badge
          style={{
            color: company.is_active ? '#86efac' : '#94a3b8',
            background: company.is_active ? 'rgba(134,239,172,.12)' : 'rgba(100,116,139,.12)',
          }}
        >
          {company.is_active ? 'פעילה' : 'מושבתת'}
        </Badge>
      </td>
      <td style={{ padding: '10px 16px' }}>
        <AttendanceToggle companyId={company.company_id} />
      </td>
      <td style={{ padding: '10px 16px', color: 'var(--muted)' }}>{fmtDate(company.created_at)}</td>
      <td style={{ padding: '10px 16px' }}>
        <div className="flex gap-2">
          {canActAs && (
            <Button variant="secondary" size="sm" onClick={onActAs}>
              <UserCog size={14} /> כניסה כמנהל חברה
            </Button>
          )}
          <Button variant="secondary" size="sm" onClick={onSettings}>
            <Settings size={14} /> הגדרות
          </Button>
          <Button variant="secondary" size="sm" onClick={onToggle}>
            {company.is_active ? 'השבת' : 'הפעל'}
          </Button>
          <Button variant="danger" size="sm" onClick={onDelete}>
            מחק
          </Button>
        </div>
      </td>
    </tr>
  )
}

export default function CompaniesPage() {
  const { companies, update, remove } = useCompanies()
  const { data: session } = useSession()
  const canActAs = session?.user?.role === 'admin'
  const [addOpen, setAddOpen] = useState(false)
  const [settingsCompany, setSettingsCompany] = useState<CompanyRead | null>(null)
  const [actAsCompany, setActAsCompany] = useState<CompanyRead | null>(null)

  return (
    <div className="animate-fade-up">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-[18px] font-bold">חברות</h1>
          <p className="text-[13px] text-faint mt-1">ניהול הדיירים (tenants) במערכת</p>
        </div>
        <Button size="sm" onClick={() => setAddOpen(true)}>
          <Plus size={14} /> הוסף חברה
        </Button>
      </div>

      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {companies.length === 0 ? (
          <div className="text-[13px] text-faint text-center py-10">אין חברות רשומות</div>
        ) : (
          <table className="w-full text-[13px]" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)' }}>
                {['שם', 'סטטוס', 'נוכחות', 'נוצרה', 'פעולות'].map((h) => (
                  <th key={h} className="text-right text-[11px] font-bold text-faint" style={{ padding: '10px 16px' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {companies.map((c) => (
                <CompanyRow
                  key={c.company_id}
                  company={c}
                  canActAs={canActAs}
                  onSettings={() => setSettingsCompany(c)}
                  onActAs={() => setActAsCompany(c)}
                  onToggle={() => update({ id: c.company_id, patch: { is_active: !c.is_active } })}
                  onDelete={() => remove(c.company_id)}
                />
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <AddCompanyDialog open={addOpen} onClose={() => setAddOpen(false)} />
      <CompanySettingsDialog company={settingsCompany} onClose={() => setSettingsCompany(null)} />
      <ActAsDialog company={actAsCompany} onClose={() => setActAsCompany(null)} />
    </div>
  )
}
