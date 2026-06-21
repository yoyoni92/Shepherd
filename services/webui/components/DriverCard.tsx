'use client'
import { useState } from 'react'
import { Truck, Trash2, Pencil, Copy, Check, ChevronDown, ChevronUp } from 'lucide-react'
import type { UiDriver, BotUserRead } from '@/lib/api/schemas'
import { daysTo, fmtDate } from '@/lib/domain'
import { Avatar } from '@/components/Avatar'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { createBotInvite } from '@/lib/api/fleet'

const DASH = '—'

function TelegramPanel({ driverId, botUsers }: { driverId: string; botUsers: BotUserRead[] }) {
  const connected = botUsers.find((u) => u.driver_id === driverId)
  const [open, setOpen] = useState(false)
  const [deepLink, setDeepLink] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleCreate = async () => {
    setLoading(true)
    try {
      const res = await createBotInvite(driverId)
      setDeepLink(res.deep_link)
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = () => {
    if (!deepLink) return
    navigator.clipboard.writeText(deepLink).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className="border-t border-line mt-3 pt-3">
      <button
        className="flex items-center justify-between w-full text-[12px] font-semibold text-faint cursor-pointer border-0 bg-transparent"
        onClick={() => setOpen((v) => !v)}
      >
        <span>חיבור טלגרם</span>
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {open && (
        <div className="mt-2.5 flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <span className="text-[12px] text-faint">סטטוס:</span>
            {connected ? (
              <span className="text-[12px] font-semibold" style={{ color: '#34d399' }}>
                מחובר ✓
              </span>
            ) : (
              <span className="text-[12px] font-semibold" style={{ color: '#64748b' }}>
                לא מחובר
              </span>
            )}
          </div>

          {!connected && (
            <>
              <Button variant="secondary" size="sm" onClick={handleCreate} disabled={loading}>
                {loading ? 'יוצר...' : '🔗 צור קישור הזמנה'}
              </Button>
              {deepLink && (
                <div className="flex items-center gap-1 min-w-0">
                  <input
                    readOnly
                    value={deepLink}
                    className="flex-1 text-[11px] ltr rounded-md border border-line bg-transparent px-2 py-1 outline-none truncate"
                    style={{ color: 'var(--muted)' }}
                  />
                  <button
                    onClick={handleCopy}
                    title="העתק"
                    className="flex items-center gap-1 text-[12px] font-semibold rounded-md cursor-pointer border-0 bg-transparent shrink-0"
                    style={{ color: copied ? '#34d399' : '#60a5fa', padding: '4px 8px' }}
                  >
                    {copied ? <Check size={13} /> : <Copy size={13} />}
                    {copied ? 'הועתק' : 'העתק'}
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

export function DriverCard({
  d,
  vehiclePlate,
  botUsers,
  onEdit,
  onRemove,
}: {
  d: UiDriver
  vehiclePlate?: string
  botUsers: BotUserRead[]
  onEdit: () => void
  onRemove: () => void
}) {
  const on = d.status === 'on'
  const licWarn = d.licExpiry != null && daysTo(d.licExpiry) < 30
  const statusColor = on ? '#34d399' : '#64748b'

  return (
    <Card style={{ padding: '17px 18px' }}>
      <div className="flex items-start justify-between gap-3 mb-[15px]">
        <div className="flex items-center gap-[13px] min-w-0">
          <Avatar id={Number(d.id) || d.name.length} name={d.name} />
          <div className="min-w-0">
            <div className="text-[15.5px] font-bold truncate">{d.name}</div>
            <div className="text-[12px] text-faint ltr">{d.phone}</div>
          </div>
        </div>
        <span
          className="inline-flex items-center gap-1.5 text-[11.5px] font-bold rounded-md whitespace-nowrap"
          style={{
            color: statusColor,
            background: on ? 'rgba(52,211,153,.1)' : 'rgba(100,116,139,.1)',
            padding: '4px 10px',
          }}
        >
          <span className="rounded-full" style={{ width: 6, height: 6, background: statusColor }} />
          {on ? 'במשמרת' : 'לא פעיל'}
        </span>
      </div>

      <div className="grid grid-cols-2 mb-3.5" style={{ gap: '11px 14px' }}>
        <div>
          <div className="text-[11px] text-faint mb-0.5">מספר רישיון</div>
          <div className="text-[13px] font-semibold ltr">{d.license}</div>
        </div>
        <div>
          <div className="text-[11px] text-faint mb-0.5">תוקף רישיון</div>
          <div className="text-[13px] font-semibold ltr" style={{ color: licWarn ? '#fbbf24' : 'var(--ink)' }}>
            {d.licExpiry ? fmtDate(d.licExpiry) : DASH}
          </div>
        </div>
        <div className="col-span-2">
          <div className="text-[11px] text-faint mb-0.5">רכב משויך</div>
          <div className="flex items-center gap-2">
            <Truck size={15} color="#60a5fa" />
            <span className="text-[13px] font-semibold ltr">{vehiclePlate ?? DASH}</span>
          </div>
        </div>
      </div>

      <div className="flex gap-2 border-t border-line pt-3">
        <Button variant="secondary" size="sm" className="flex-1" onClick={onEdit}>
          <Pencil size={14} />
          עריכה
        </Button>
        <Button variant="danger" size="sm" onClick={onRemove}>
          <Trash2 size={14} />
          הסר
        </Button>
      </div>

      <TelegramPanel driverId={d.id} botUsers={botUsers} />
    </Card>
  )
}
