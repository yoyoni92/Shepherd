'use client'
import { useState } from 'react'
import { Copy, Check } from 'lucide-react'
import { useBotUsers, useBotInvites } from '@/hooks/useBotManagement'
import type { BotUserRead, BotInviteRead } from '@/lib/api/schemas'
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

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }
  return (
    <button
      onClick={copy}
      title="העתק"
      className="flex items-center gap-1 text-[12px] font-semibold rounded-md cursor-pointer border-0 bg-transparent"
      style={{ color: copied ? '#34d399' : '#60a5fa', padding: '4px 8px' }}
    >
      {copied ? <Check size={13} /> : <Copy size={13} />}
      {copied ? 'הועתק' : 'העתק'}
    </button>
  )
}

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
                {['שם נהג', 'תפקיד', 'Telegram ID', 'תאריך הצטרפות', 'פעולות'].map((h) => (
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

function InviteRow({
  invite,
  onRevoke,
  onRenew,
}: {
  invite: BotInviteRead
  onRevoke: () => void
  onRenew: () => void
}) {
  return (
    <tr style={{ borderBottom: '1px solid var(--line)' }}>
      <td style={{ padding: '10px 16px' }}>{invite.driver_name ?? '—'}</td>
      <td style={{ padding: '10px 16px' }}>
        <div className="flex items-center gap-1 min-w-0">
          <span
            className="text-[12px] ltr truncate"
            style={{ color: 'var(--muted)', maxWidth: 260, display: 'inline-block' }}
            title={invite.token}
          >
            {invite.token}
          </span>
          <CopyButton text={invite.token} />
        </div>
      </td>
      <td style={{ padding: '10px 16px', color: 'var(--muted)' }}>{fmtDate(invite.expires_at)}</td>
      <td style={{ padding: '10px 16px' }}>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={onRenew}>
            חדש
          </Button>
          <Button variant="danger" size="sm" onClick={onRevoke}>
            בטל
          </Button>
        </div>
      </td>
    </tr>
  )
}

function BotInvitesSection() {
  const { invites, revokeInvite, createInvite } = useBotInvites()

  return (
    <section>
      <h2 className="text-[15px] font-bold mb-3">הזמנות ממתינות</h2>
      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {invites.length === 0 ? (
          <div className="text-[13px] text-faint text-center py-10">אין הזמנות פעילות</div>
        ) : (
          <table className="w-full text-[13px]" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)' }}>
                {['שם נהג', 'קישור הזמנה', 'תפוגף ב', 'פעולות'].map((h) => (
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
              {invites.map((invite) => (
                <InviteRow
                  key={invite.token}
                  invite={invite}
                  onRevoke={() => revokeInvite(invite.token)}
                  onRenew={() => createInvite(invite.driver_id)}
                />
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </section>
  )
}

export default function BotPage() {
  return (
    <div className="animate-fade-up">
      <div className="mb-6">
        <h1 className="text-[18px] font-bold">ניהול בוט</h1>
        <p className="text-[13px] text-faint mt-1">ניהול משתמשי הטלגרם והזמנות</p>
      </div>

      <BotUsersSection />
      <BotInvitesSection />
    </div>
  )
}
