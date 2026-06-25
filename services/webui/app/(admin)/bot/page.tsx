'use client'
import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useBotUsers, useBotAuthorizations } from '@/hooks/useBotManagement'
import { useDrivers } from '@/hooks/useDrivers'
import type { BotUserRead, BotAuthorizationRead } from '@/lib/api/schemas'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogClose,
} from '@/components/ui/dialog'
import { fmtDate } from '@/lib/domain'

function RoleBadge({ role }: { role: 'admin' | 'driver' }) {
  const isAdmin = role === 'admin'
  return (
    <Badge
      style={{
        color: isAdmin ? '#93c5fd' : '#94a3b8',
        background: isAdmin ? 'rgba(147,197,253,.12)' : 'rgba(100,116,139,.12)',
      }}
    >
      {isAdmin ? 'אדמין' : 'נהג'}
    </Badge>
  )
}

function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  onConfirm,
  onClose,
}: {
  open: boolean
  title: string
  description: string
  confirmLabel: string
  onConfirm: () => void
  onClose: () => void
}) {
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent style={{ maxWidth: 420 }}>
        <div className="p-6 flex flex-col gap-4">
          <DialogTitle className="text-[16px] font-bold">{title}</DialogTitle>
          <p className="text-[13px] text-faint">{description}</p>
          <div className="flex gap-2 justify-end mt-2">
            <DialogClose asChild>
              <Button variant="secondary" size="sm" onClick={onClose}>
                ביטול
              </Button>
            </DialogClose>
            <Button
              size="sm"
              onClick={() => {
                onConfirm()
                onClose()
              }}
            >
              {confirmLabel}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function BotUsersSection() {
  const { users, updateRole } = useBotUsers()
  const [confirm, setConfirm] = useState<{ user: BotUserRead; newRole: 'admin' | 'driver' } | null>(null)

  return (
    <section className="mb-8">
      <h2 className="text-[15px] font-bold mb-3">משתמשי הבוט</h2>
      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {users.length === 0 ? (
          <div className="text-[13px] text-faint text-center py-10">אין משתמשי בוט רשומים</div>
        ) : (
          <table className="w-full text-[13px]" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)' }}>
                {['שם נהג', 'תפקיד', 'טלפון', 'Telegram ID', 'תאריך הצטרפות', 'פעולות'].map((h) => (
                  <th
                    key={h}
                    className="text-right text-[11px] font-bold text-faint"
                    style={{ padding: '10px 16px' }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const newRole = u.role === 'admin' ? 'driver' : 'admin'
                const actionLabel = u.role === 'admin' ? 'שנה לנהג' : 'שנה לאדמין'
                return (
                  <tr
                    key={u.user_id}
                    style={{ borderBottom: '1px solid var(--line)' }}
                  >
                    <td style={{ padding: '10px 16px' }}>{u.driver_name ?? '—'}</td>
                    <td style={{ padding: '10px 16px' }}>
                      <RoleBadge role={u.role} />
                    </td>
                    <td className="ltr" style={{ padding: '10px 16px', color: 'var(--muted)' }}>
                      {u.phone_number ?? '—'}
                    </td>
                    <td className="ltr" style={{ padding: '10px 16px', color: 'var(--muted)' }}>
                      {u.telegram_chat_id}
                    </td>
                    <td style={{ padding: '10px 16px', color: 'var(--muted)' }}>
                      {fmtDate(u.created_at)}
                    </td>
                    <td style={{ padding: '10px 16px' }}>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setConfirm({ user: u, newRole })}
                      >
                        {actionLabel}
                      </Button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </Card>

      {confirm && (
        <ConfirmDialog
          open={true}
          title="שינוי תפקיד"
          description={`האם לשנות את תפקיד ${confirm.user.driver_name ?? 'המשתמש'} ל-${confirm.newRole === 'admin' ? 'אדמין' : 'נהג'}?`}
          confirmLabel="אישור"
          onConfirm={() =>
            updateRole({ userId: confirm.user.user_id, role: confirm.newRole })
          }
          onClose={() => setConfirm(null)}
        />
      )}
    </section>
  )
}

function AuthorizationRow({
  authz,
  onRevoke,
}: {
  authz: BotAuthorizationRead
  onRevoke: () => void
}) {
  return (
    <tr style={{ borderBottom: '1px solid var(--line)' }}>
      <td style={{ padding: '10px 16px' }}>{authz.driver_name ?? '—'}</td>
      <td style={{ padding: '10px 16px' }}>
        <RoleBadge role={authz.role} />
      </td>
      <td className="ltr" style={{ padding: '10px 16px', color: 'var(--muted)' }}>{authz.phone_number}</td>
      <td style={{ padding: '10px 16px', color: 'var(--muted)' }}>
        {authz.expires_at ? fmtDate(authz.expires_at) : 'קבוע'}
      </td>
      <td style={{ padding: '10px 16px' }}>
        <Button variant="danger" size="sm" onClick={onRevoke}>
          בטל
        </Button>
      </td>
    </tr>
  )
}

function AddAuthorizationDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { createAuthorization } = useBotAuthorizations()
  const { drivers } = useDrivers()
  const [role, setRole] = useState<'admin' | 'driver'>('admin')
  const [driverId, setDriverId] = useState('')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [expiresAt, setExpiresAt] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const close = () => {
    setRole('admin')
    setDriverId('')
    setPhoneNumber('')
    setExpiresAt('')
    setErr(null)
    onClose()
  }

  const submit = async () => {
    setErr(null)
    if (!phoneNumber.trim()) {
      setErr('יש להזין מספר טלפון')
      return
    }
    setBusy(true)
    try {
      await createAuthorization({
        phoneNumber: phoneNumber.trim(),
        role,
        driverId: driverId || undefined,
        // Empty = permanent; a date means the role lapses at end of that day.
        expiresAt: expiresAt ? new Date(`${expiresAt}T23:59:59`).toISOString() : undefined,
      })
      close()
    } catch {
      setErr('יצירת ההרשאה נכשלה')
      setBusy(false)
    }
  }

  const fieldStyle = {
    background: 'var(--panel-2, #0f172a)',
    color: 'var(--muted)',
    border: '1px solid var(--line)',
  } as const

  return (
    <Dialog open={open} onOpenChange={(v) => !v && close()}>
      <DialogContent style={{ maxWidth: 460 }}>
        <div className="p-6 flex flex-col gap-4">
          <DialogTitle className="text-[16px] font-bold">הוספת הרשאה</DialogTitle>
          <p className="text-[13px] text-faint">
            הוסף/י הרשאה לפי מספר טלפון. בכניסה הראשונה לבוט המשתמש ישתף את הטלפון ויזוהה אוטומטית.
          </p>
          <div className="flex flex-col gap-2">
            <label className="text-[12px] font-semibold text-faint">תפקיד</label>
            <div className="flex gap-2">
              <Button variant={role === 'admin' ? 'primary' : 'secondary'} size="sm" onClick={() => setRole('admin')}>
                אדמין
              </Button>
              <Button variant={role === 'driver' ? 'primary' : 'secondary'} size="sm" onClick={() => setRole('driver')}>
                נהג
              </Button>
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-[12px] font-semibold text-faint">קישור לנהג (אופציונלי)</label>
            <select
              value={driverId}
              onChange={(e) => setDriverId(e.target.value)}
              className="text-[13px] rounded-md px-2 py-2"
              style={fieldStyle}
            >
              <option value="">— ללא —</option>
              {drivers.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-[12px] font-semibold text-faint">מספר טלפון (חובה)</label>
            <input
              type="tel"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="0501234567"
              className="text-[13px] rounded-md px-2 py-2 ltr"
              style={fieldStyle}
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-[12px] font-semibold text-faint">תוקף עד (אופציונלי - ריק = קבוע)</label>
            <input
              type="date"
              value={expiresAt}
              onChange={(e) => setExpiresAt(e.target.value)}
              className="text-[13px] rounded-md px-2 py-2 ltr"
              style={fieldStyle}
            />
          </div>
          {err && (
            <p className="text-[12px]" style={{ color: '#f87171' }}>
              {err}
            </p>
          )}
          <div className="flex gap-2 justify-end mt-2">
            <DialogClose asChild>
              <Button variant="secondary" size="sm" onClick={close}>
                ביטול
              </Button>
            </DialogClose>
            <Button size="sm" disabled={busy} onClick={submit}>
              {busy ? 'יוצר…' : 'הוסף הרשאה'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function BotAuthorizationsSection() {
  const { authorizations, revokeAuthorization } = useBotAuthorizations()
  const [addOpen, setAddOpen] = useState(false)

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-[15px] font-bold">הרשאות גישה</h2>
        <Button size="sm" onClick={() => setAddOpen(true)}>
          <Plus size={14} /> הוסף הרשאה
        </Button>
      </div>
      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {authorizations.length === 0 ? (
          <div className="text-[13px] text-faint text-center py-10">
            אין הרשאות נוספות. נהגים פעילים מקבלים גישה אוטומטית.
          </div>
        ) : (
          <table className="w-full text-[13px]" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)' }}>
                {['שם נהג', 'תפקיד', 'טלפון', 'תוקף עד', 'פעולות'].map((h) => (
                  <th
                    key={h}
                    className="text-right text-[11px] font-bold text-faint"
                    style={{ padding: '10px 16px' }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {authorizations.map((authz) => (
                <AuthorizationRow
                  key={authz.id}
                  authz={authz}
                  onRevoke={() => revokeAuthorization(authz.id)}
                />
              ))}
            </tbody>
          </table>
        )}
      </Card>
      <AddAuthorizationDialog open={addOpen} onClose={() => setAddOpen(false)} />
    </section>
  )
}

export default function BotPage() {
  return (
    <div className="animate-fade-up">
      <div className="mb-6">
        <h1 className="text-[18px] font-bold">ניהול בוט</h1>
        <p className="text-[13px] text-faint mt-1">משתמשי הטלגרם והרשאות הגישה</p>
      </div>

      <BotUsersSection />
      <BotAuthorizationsSection />
    </div>
  )
}
