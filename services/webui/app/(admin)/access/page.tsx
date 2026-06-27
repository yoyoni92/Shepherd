'use client'
import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useAppUsers } from '@/hooks/useAppUsers'
import { useCompanies } from '@/hooks/useCompanies'
import type { AppUserRead } from '@/lib/api/schemas'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogTitle, DialogClose } from '@/components/ui/dialog'

const fieldStyle = {
  background: 'var(--panel-2, #0f172a)',
  color: 'var(--muted)',
  border: '1px solid var(--line)',
} as const

const ROLE_LABEL: Record<string, string> = { admin: 'מנהל מערכת', company_admin: 'מנהל חברה' }

function AddUserDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { add } = useAppUsers()
  const { companies } = useCompanies()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [role, setRole] = useState<'admin' | 'company_admin'>('company_admin')
  const [companyId, setCompanyId] = useState('')
  const [isSystemAdmin, setIsSystemAdmin] = useState(false)
  const [phoneNumber, setPhoneNumber] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const close = () => {
    setEmail('')
    setPassword('')
    setName('')
    setRole('company_admin')
    setCompanyId('')
    setIsSystemAdmin(false)
    setPhoneNumber('')
    setErr(null)
    onClose()
  }

  // A system admin has no company and is always role=admin.
  const effectiveRole = isSystemAdmin ? 'admin' : role

  const submit = async () => {
    setErr(null)
    if (!email.trim() || !password.trim()) {
      setErr('יש להזין דוא״ל וסיסמה')
      return
    }
    if (!isSystemAdmin && effectiveRole === 'company_admin' && !companyId) {
      setErr('יש לבחור חברה למנהל חברה')
      return
    }
    setBusy(true)
    try {
      await add({
        email: email.trim(),
        password: password.trim(),
        role: effectiveRole,
        name: name.trim() || null,
        company_id: isSystemAdmin || effectiveRole !== 'company_admin' ? null : companyId,
        is_system_admin: isSystemAdmin,
        phone_number: phoneNumber.trim() || null,
      })
      close()
    } catch {
      setErr('יצירת המשתמש נכשלה')
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && close()}>
      <DialogContent style={{ maxWidth: 460 }}>
        <div className="p-6 flex flex-col gap-4">
          <DialogTitle className="text-[16px] font-bold">הוספת משתמש גישה</DialogTitle>
          <div className="flex flex-col gap-2">
            <label className="text-[12px] font-semibold text-faint">דוא״ל</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="text-[13px] rounded-md px-2 py-2 ltr"
              style={fieldStyle}
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-[12px] font-semibold text-faint">סיסמה</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="text-[13px] rounded-md px-2 py-2 ltr"
              style={fieldStyle}
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-[12px] font-semibold text-faint">שם (אופציונלי)</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="text-[13px] rounded-md px-2 py-2"
              style={fieldStyle}
            />
          </div>
          <label className="flex items-center gap-2 text-[13px] font-semibold cursor-pointer">
            <input
              type="checkbox"
              checked={isSystemAdmin}
              onChange={(e) => setIsSystemAdmin(e.target.checked)}
            />
            מנהל מערכת
          </label>
          <div className="flex flex-col gap-2">
            <label className="text-[12px] font-semibold text-faint">טלפון (אופציונלי)</label>
            <input
              type="tel"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              className="text-[13px] rounded-md px-2 py-2 ltr"
              style={fieldStyle}
            />
          </div>
          {!isSystemAdmin && (
            <div className="flex flex-col gap-2">
              <label className="text-[12px] font-semibold text-faint">תפקיד</label>
              <div className="flex gap-2">
                <Button variant={role === 'admin' ? 'primary' : 'secondary'} size="sm" onClick={() => setRole('admin')}>
                  מנהל מערכת
                </Button>
                <Button
                  variant={role === 'company_admin' ? 'primary' : 'secondary'}
                  size="sm"
                  onClick={() => setRole('company_admin')}
                >
                  מנהל חברה
                </Button>
              </div>
            </div>
          )}
          {!isSystemAdmin && role === 'company_admin' && (
            <div className="flex flex-col gap-2">
              <label className="text-[12px] font-semibold text-faint">חברה</label>
              <select
                value={companyId}
                onChange={(e) => setCompanyId(e.target.value)}
                className="text-[13px] rounded-md px-2 py-2"
                style={fieldStyle}
              >
                <option value="">— בחר/י חברה —</option>
                {companies.map((c) => (
                  <option key={c.company_id} value={c.company_id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          {err && <p className="text-[12px]" style={{ color: '#f87171' }}>{err}</p>}
          <div className="flex gap-2 justify-end mt-2">
            <DialogClose asChild>
              <Button variant="secondary" size="sm" onClick={close}>
                ביטול
              </Button>
            </DialogClose>
            <Button size="sm" disabled={busy} onClick={submit}>
              {busy ? 'יוצר…' : 'הוסף משתמש'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function ResetPasswordDialog({ user, onClose }: { user: AppUserRead; onClose: () => void }) {
  const { update } = useAppUsers()
  const [password, setPassword] = useState('')
  const [err, setErr] = useState<string | null>(null)

  const submit = () => {
    if (!password.trim()) {
      setErr('יש להזין סיסמה חדשה')
      return
    }
    update({ id: user.user_id, patch: { password: password.trim() } })
    onClose()
  }

  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent style={{ maxWidth: 420 }}>
        <div className="p-6 flex flex-col gap-4">
          <DialogTitle className="text-[16px] font-bold">איפוס סיסמה</DialogTitle>
          <p className="text-[13px] text-faint">
            סיסמה חדשה עבור <span className="ltr">{user.email}</span>
          </p>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="text-[13px] rounded-md px-2 py-2 ltr"
            style={fieldStyle}
          />
          {err && <p className="text-[12px]" style={{ color: '#f87171' }}>{err}</p>}
          <div className="flex gap-2 justify-end mt-2">
            <DialogClose asChild>
              <Button variant="secondary" size="sm" onClick={onClose}>
                ביטול
              </Button>
            </DialogClose>
            <Button size="sm" onClick={submit}>
              עדכן סיסמה
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function EditUserDialog({ user, onClose }: { user: AppUserRead; onClose: () => void }) {
  const { update } = useAppUsers()
  const [name, setName] = useState(user.name ?? '')
  const [phoneNumber, setPhoneNumber] = useState(user.phone_number ?? '')
  const [isSystemAdmin, setIsSystemAdmin] = useState(user.is_system_admin)
  const [isActive, setIsActive] = useState(user.is_active)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const submit = async () => {
    setErr(null)
    setBusy(true)
    try {
      await update({
        id: user.user_id,
        patch: {
          name: name.trim() || null,
          phone_number: phoneNumber.trim() || null,
          is_system_admin: isSystemAdmin,
          is_active: isActive,
        },
      })
      onClose()
    } catch {
      setErr('עדכון המשתמש נכשל')
      setBusy(false)
    }
  }

  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent style={{ maxWidth: 460 }}>
        <div className="p-6 flex flex-col gap-4">
          <DialogTitle className="text-[16px] font-bold">עריכת משתמש גישה</DialogTitle>
          <p className="text-[13px] text-faint">
            <span className="ltr">{user.email}</span> · {ROLE_LABEL[user.role] ?? user.role}
          </p>
          <div className="flex flex-col gap-2">
            <label className="text-[12px] font-semibold text-faint">שם</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="text-[13px] rounded-md px-2 py-2"
              style={fieldStyle}
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-[12px] font-semibold text-faint">טלפון</label>
            <input
              type="tel"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              className="text-[13px] rounded-md px-2 py-2 ltr"
              style={fieldStyle}
            />
          </div>
          <label className="flex items-center gap-2 text-[13px] font-semibold cursor-pointer">
            <input
              type="checkbox"
              checked={isSystemAdmin}
              onChange={(e) => setIsSystemAdmin(e.target.checked)}
            />
            מנהל מערכת
          </label>
          <label className="flex items-center gap-2 text-[13px] font-semibold cursor-pointer">
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            פעיל
          </label>
          <p className="text-[11px] text-faint">תפקיד וחברה נקבעים ביצירה ואינם ניתנים לשינוי כאן.</p>
          {err && <p className="text-[12px]" style={{ color: '#f87171' }}>{err}</p>}
          <div className="flex gap-2 justify-end mt-2">
            <DialogClose asChild>
              <Button variant="secondary" size="sm" onClick={onClose}>
                ביטול
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

function UserRow({
  user,
  onEdit,
  onReset,
  onToggle,
  onDelete,
}: {
  user: AppUserRead
  onEdit: () => void
  onReset: () => void
  onToggle: () => void
  onDelete: () => void
}) {
  return (
    <tr style={{ borderBottom: '1px solid var(--line)' }}>
      <td className="ltr" style={{ padding: '10px 16px' }}>{user.email}</td>
      <td style={{ padding: '10px 16px' }}>{user.name ?? '—'}</td>
      <td className="ltr" style={{ padding: '10px 16px', color: 'var(--muted)' }}>{user.phone_number ?? '—'}</td>
      <td style={{ padding: '10px 16px', color: 'var(--muted)' }}>
        <div className="flex items-center gap-2">
          <span>{ROLE_LABEL[user.role] ?? user.role}</span>
          {user.is_system_admin && (
            <Badge style={{ color: '#c4b5fd', background: 'rgba(167,139,250,.14)' }}>מנהל מערכת</Badge>
          )}
        </div>
      </td>
      <td style={{ padding: '10px 16px' }}>
        <Badge
          style={{
            color: user.is_active ? '#86efac' : '#94a3b8',
            background: user.is_active ? 'rgba(134,239,172,.12)' : 'rgba(100,116,139,.12)',
          }}
        >
          {user.is_active ? 'פעיל' : 'מושבת'}
        </Badge>
      </td>
      <td style={{ padding: '10px 16px' }}>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={onEdit}>
            ערוך
          </Button>
          <Button variant="secondary" size="sm" onClick={onReset}>
            איפוס סיסמה
          </Button>
          <Button variant="secondary" size="sm" onClick={onToggle}>
            {user.is_active ? 'השבת' : 'הפעל'}
          </Button>
          <Button variant="danger" size="sm" onClick={onDelete}>
            מחק
          </Button>
        </div>
      </td>
    </tr>
  )
}

export default function AccessPage() {
  const { users, update, remove } = useAppUsers()
  const [addOpen, setAddOpen] = useState(false)
  const [resetUser, setResetUser] = useState<AppUserRead | null>(null)
  const [editUser, setEditUser] = useState<AppUserRead | null>(null)

  return (
    <div className="animate-fade-up">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-[18px] font-bold">משתמשי גישה</h1>
          <p className="text-[13px] text-faint mt-1">ניהול כניסות מנהלי מערכת ומנהלי חברה לקונסולה</p>
        </div>
        <Button size="sm" onClick={() => setAddOpen(true)}>
          <Plus size={14} /> הוסף משתמש
        </Button>
      </div>

      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {users.length === 0 ? (
          <div className="text-[13px] text-faint text-center py-10">אין משתמשי גישה רשומים</div>
        ) : (
          <table className="w-full text-[13px]" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)' }}>
                {['דוא״ל', 'שם', 'טלפון', 'תפקיד', 'סטטוס', 'פעולות'].map((h) => (
                  <th key={h} className="text-right text-[11px] font-bold text-faint" style={{ padding: '10px 16px' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <UserRow
                  key={u.user_id}
                  user={u}
                  onEdit={() => setEditUser(u)}
                  onReset={() => setResetUser(u)}
                  onToggle={() => update({ id: u.user_id, patch: { is_active: !u.is_active } })}
                  onDelete={() => remove(u.user_id)}
                />
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <AddUserDialog open={addOpen} onClose={() => setAddOpen(false)} />
      {editUser && <EditUserDialog user={editUser} onClose={() => setEditUser(null)} />}
      {resetUser && <ResetPasswordDialog user={resetUser} onClose={() => setResetUser(null)} />}
    </div>
  )
}
