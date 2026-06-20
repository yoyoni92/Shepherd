'use client'
import { X } from 'lucide-react'
import { aggregate, hoursFor, type AttendanceDay, type AttendanceMonth, type Employee } from '@/lib/attendance'
import { Avatar } from '@/components/Avatar'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

const STATUS_ACCENT: Record<AttendanceDay['status'], string> = {
  present: '#34d399',
  late: '#fbbf24',
  leave: '#a78bfa',
  absent: '#f87171',
}

interface Props {
  month: AttendanceMonth
  employee: Employee
  monthLabel: string
  onPatch: (employeeId: string, day: number, patch: Partial<AttendanceDay>) => void
  onClose: () => void
}

export function AttendanceEditModal({ month, employee, monthLabel, onPatch, onClose }: Props) {
  const avatarId = Number(employee.id) || employee.name.length
  const days = month.records[employee.id] ?? []
  const a = aggregate(days)

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <div className="flex items-center gap-[13px] border-b border-line" style={{ padding: '18px 22px' }}>
          <Avatar id={avatarId} name={employee.name} size={42} radius={11} font={15} />
          <div className="flex-1 min-w-0">
            <DialogTitle className="text-[16px] font-extrabold">{employee.name}</DialogTitle>
            <div className="text-[12px] text-faint">
              {employee.role} · {monthLabel}
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="סגור"
            className="w-[34px] h-[34px] rounded-lg bg-panel2 border border-control text-muted cursor-pointer flex items-center justify-center"
          >
            <X size={17} />
          </button>
        </div>

        <div
          className="grid text-[11px] font-bold text-faint border-b border-divider"
          style={{ gridTemplateColumns: '3px 1.4fr 1fr 1fr 1.2fr 64px', gap: 10, padding: '11px 22px' }}
        >
          <div />
          <div>תאריך</div>
          <div>כניסה</div>
          <div>יציאה</div>
          <div>סטטוס</div>
          <div className="text-left">שעות</div>
        </div>

        <div className="flex-1 overflow-y-auto" style={{ padding: '4px 22px 12px' }}>
          {days.map((d) => {
            const h = hoursFor(d)
            return (
              <div
                key={d.day}
                className="grid items-center border-b border-divider"
                style={{ gridTemplateColumns: '3px 1.4fr 1fr 1fr 1.2fr 64px', gap: 10, padding: '7px 0' }}
              >
                <div style={{ minWidth: 3, width: 3, height: 30, borderRadius: 3, background: STATUS_ACCENT[d.status] }} />
                <div>
                  <div className="text-[13px] font-semibold ltr">{d.dateLabel}</div>
                  <div className="text-[10.5px] text-faint">יום {d.weekday}</div>
                </div>
                <input
                  type="time"
                  value={d.in}
                  onChange={(e) => onPatch(employee.id, d.day, { in: e.target.value })}
                  className="bg-bg border border-control rounded-[7px] text-[12.5px] text-ink outline-none w-full"
                  style={{ padding: '6px 8px' }}
                />
                <input
                  type="time"
                  value={d.out}
                  onChange={(e) => onPatch(employee.id, d.day, { out: e.target.value })}
                  className="bg-bg border border-control rounded-[7px] text-[12.5px] text-ink outline-none w-full"
                  style={{ padding: '6px 8px' }}
                />
                <select
                  value={d.status}
                  onChange={(e) => onPatch(employee.id, d.day, { status: e.target.value as AttendanceDay['status'] })}
                  className="bg-bg border border-control rounded-[7px] text-[12.5px] text-ink outline-none w-full"
                  style={{ padding: '6px 8px' }}
                >
                  <option value="present">נוכח</option>
                  <option value="late">איחור</option>
                  <option value="leave">חופשה</option>
                  <option value="absent">היעדרות</option>
                </select>
                <div className="text-left text-[12.5px] font-bold text-success">{h ? `${h} ש׳` : '—'}</div>
              </div>
            )
          })}
        </div>

        <div className="flex items-center gap-3.5 border-t border-line" style={{ padding: '15px 22px' }}>
          <div className="text-[12.5px] text-muted">
            {a.pres} ימי עבודה · {a.hours} שעות · {a.late} איחורים
          </div>
          <div className="flex-1" />
          <Button onClick={onClose}>שמירה וסגירה</Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
