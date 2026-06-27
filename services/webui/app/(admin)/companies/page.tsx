'use client'
import { useEffect, useState } from 'react'
import { Plus, Settings } from 'lucide-react'
import { useCompanies } from '@/hooks/useCompanies'
import { useCompanySettings } from '@/hooks/useCompanySettings'
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

function CompanySettingsDialog({ company, onClose }: { company: CompanyRead | null; onClose: () => void }) {
  const { settings, save } = useCompanySettings(company?.company_id ?? null)
  const [folderId, setFolderId] = useState('')
  const [creds, setCreds] = useState('')
  const [attendance, setAttendance] = useState(false)
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
    setAttendance(settings.feature_flags?.attendance === true)
    setCreds('')
  }, [settings])

  const submit = async () => {
    setErr(null)
    setOk(false)
    setBusy(true)
    const patch: CompanySettingsUpdate = {
      gdrive_folder_id: folderId.trim() || null,
      feature_flags: { attendance },
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
      <DialogContent style={{ maxWidth: 480 }}>
        <div className="p-6 flex flex-col gap-4">
          <DialogTitle className="text-[16px] font-bold">הגדרות · {company?.name}</DialogTitle>

          <div className="flex flex-col gap-2">
            <label className="text-[12px] font-semibold text-faint">מזהה תיקיית Google Drive</label>
            <input
              value={folderId}
              onChange={(e) => setFolderId(e.target.value)}
              className="text-[13px] rounded-md px-2 py-2"
              style={fieldStyle}
            />
          </div>

          <div className="flex flex-col gap-2">
            <label className="text-[12px] font-semibold text-faint">
              פרטי חשבון שירות (JSON)
              {settings?.gdrive_configured && (
                <span className="mr-2 text-[11px]" style={{ color: '#86efac' }}>מוגדר ✓</span>
              )}
            </label>
            <textarea
              value={creds}
              onChange={(e) => setCreds(e.target.value)}
              rows={4}
              placeholder={settings?.gdrive_configured ? 'הדבק/י JSON חדש כדי להחליף' : 'הדבק/י את ה-JSON'}
              className="text-[12px] rounded-md px-2 py-2 font-mono"
              style={fieldStyle}
            />
          </div>

          <label className="flex items-center gap-2 text-[13px] cursor-pointer">
            <input type="checkbox" checked={attendance} onChange={(e) => setAttendance(e.target.checked)} />
            <span>נוכחות מופעלת</span>
          </label>

          {err && <p className="text-[12px]" style={{ color: '#f87171' }}>{err}</p>}
          {ok && <p className="text-[12px]" style={{ color: '#86efac' }}>ההגדרות נשמרו ✓</p>}

          <div className="flex gap-2 justify-end mt-2">
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

function CompanyRow({ company, onSettings, onToggle, onDelete }: { company: CompanyRead; onSettings: () => void; onToggle: () => void; onDelete: () => void }) {
  return (
    <tr style={{ borderBottom: '1px solid var(--line)' }}>
      <td style={{ padding: '10px 16px' }}>{company.name}</td>
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
      <td style={{ padding: '10px 16px', color: 'var(--muted)' }}>{fmtDate(company.created_at)}</td>
      <td style={{ padding: '10px 16px' }}>
        <div className="flex gap-2">
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
  const [addOpen, setAddOpen] = useState(false)
  const [settingsCompany, setSettingsCompany] = useState<CompanyRead | null>(null)

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
                {['שם', 'סטטוס', 'נוצרה', 'פעולות'].map((h) => (
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
                  onSettings={() => setSettingsCompany(c)}
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
    </div>
  )
}
