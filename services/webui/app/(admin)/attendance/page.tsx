'use client'
import { useState } from 'react'
import { ChevronLeft, ChevronRight, Download, FileText, Pencil } from 'lucide-react'
import { useAttendance } from '@/hooks/useAttendance'
import { aggregate, summarize, employeeStatus, buildCsv, monthOptions, type AttendanceDay } from '@/lib/attendance'
import { Card } from '@/components/ui/card'
import { Avatar } from '@/components/Avatar'
import { ATT_STATUS_META } from '@/components/meta'
import { AttendanceEditModal } from '@/components/AttendanceEditModal'

const GRID = '2fr 88px 116px 116px 86px 78px 108px 64px'
const MONTHS = monthOptions(3)

export default function AttendancePage() {
  const [idx, setIdx] = useState(MONTHS.length - 1)
  const [editId, setEditId] = useState<string | null>(null)
  const current = MONTHS[idx]
  const { month, loading, patchDay } = useAttendance(current.key)

  const label = month?.label ?? current.label
  const employees = month?.employees ?? []
  const records = month?.records ?? {}
  const summary = summarize(employees, records)

  const onPatch = (employeeId: string, day: number, patch: Partial<AttendanceDay>) =>
    patchDay({ employeeId, day, patch })

  const exportCsv = () => {
    const csv = buildCsv(employees, records)
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `attendance_${current.key}.csv`
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  const editEmployee = employees.find((e) => e.id === editId) ?? null

  const KPIS = [
    { value: String(summary.empCount), label: 'עובדים פעילים', color: '#60a5fa' },
    { value: `${summary.totalHours} ש׳`, label: 'סך שעות החודש', color: '#34d399' },
    { value: `${summary.avgPerEmp} ש׳`, label: 'ממוצע לעובד', color: '#a78bfa' },
    { value: String(summary.totalLate), label: 'איחורים החודש', color: '#fbbf24' },
  ]

  return (
    <div className="animate-fade-up">
      <div className="flex items-center gap-3 mb-5 flex-wrap">
        <div className="flex items-center gap-1 bg-panel border border-control rounded-[10px]" style={{ padding: 5 }}>
          <button
            aria-label="חודש קודם"
            onClick={() => setIdx((i) => Math.max(0, i - 1))}
            className="w-8 h-8 rounded-[7px] bg-panel2 border-0 text-muted cursor-pointer flex items-center justify-center"
          >
            <ChevronRight size={16} />
          </button>
          <div className="text-center text-[14px] font-bold" style={{ minWidth: 118 }}>
            {label}
          </div>
          <button
            aria-label="חודש הבא"
            onClick={() => setIdx((i) => Math.min(MONTHS.length - 1, i + 1))}
            className="w-8 h-8 rounded-[7px] bg-panel2 border-0 text-muted cursor-pointer flex items-center justify-center"
          >
            <ChevronLeft size={16} />
          </button>
        </div>
        <div className="flex-1" />
        <button
          onClick={exportCsv}
          className="flex items-center gap-[7px] bg-panel2 border border-control rounded-[9px] text-[13px] font-bold text-success cursor-pointer"
          style={{ padding: '10px 15px' }}
        >
          <Download size={15} />
          ייצוא CSV
        </button>
        <button
          onClick={() => window.print()}
          className="flex items-center gap-[7px] bg-panel2 border border-control rounded-[9px] text-[13px] font-bold text-pink cursor-pointer"
          style={{ padding: '10px 15px' }}
        >
          <FileText size={15} />
          ייצוא PDF
        </button>
      </div>

      <div className="grid gap-3.5 mb-[18px]" style={{ gridTemplateColumns: 'repeat(4,1fr)' }}>
        {KPIS.map((k) => (
          <Card key={k.label} className="rounded-[13px]" style={{ padding: '16px 18px' }}>
            <div className="text-[27px] font-extrabold leading-none" style={{ color: k.color, letterSpacing: '-.5px' }}>
              {k.value}
            </div>
            <div className="text-[12.5px] text-muted mt-[5px]">{k.label}</div>
          </Card>
        ))}
      </div>

      <Card className="overflow-hidden">
        <div
          className="grid text-[11.5px] font-bold text-faint border-b border-line"
          style={{ gridTemplateColumns: GRID, gap: 10, padding: '14px 18px' }}
        >
          <div>עובד</div>
          <div className="text-center">ימי עבודה</div>
          <div className="text-center">כניסה ממוצעת</div>
          <div className="text-center">יציאה ממוצעת</div>
          <div className="text-center">סך שעות</div>
          <div className="text-center">איחורים</div>
          <div className="text-center">סטטוס</div>
          <div className="text-center">עריכה</div>
        </div>

        {loading && <div className="text-faint text-sm" style={{ padding: '16px 18px' }}>טוען…</div>}

        {employees.map((e) => {
          const a = aggregate(records[String(e.id)] ?? [])
          const st = ATT_STATUS_META[employeeStatus(a)]
          return (
            <div
              key={e.id}
              className="grid items-center border-b border-divider"
              style={{ gridTemplateColumns: GRID, gap: 10, padding: '12px 18px' }}
            >
              <div className="flex items-center gap-[11px] min-w-0">
                <Avatar id={Number(e.id) || e.name.length} name={e.name} size={38} radius={10} font={13} />
                <div className="min-w-0">
                  <div className="text-[13.5px] font-bold truncate">{e.name}</div>
                  <div className="text-[11.5px] text-faint">{e.role}</div>
                </div>
              </div>
              <div className="text-center text-[13.5px] font-bold">{a.pres}</div>
              <div className="text-center text-[13px] ltr">{a.avgIn}</div>
              <div className="text-center text-[13px] ltr">{a.avgOut}</div>
              <div className="text-center text-[13.5px] font-bold text-success">{a.hours}</div>
              <div className="text-center text-[13.5px] font-bold text-warning">{a.late}</div>
              <div className="text-center">
                <span
                  className="text-[11.5px] font-bold rounded-md whitespace-nowrap inline-block"
                  style={{ color: st.color, background: st.bg, padding: '4px 10px' }}
                >
                  {st.label}
                </span>
              </div>
              <div className="flex justify-center">
                <button
                  onClick={() => setEditId(e.id)}
                  title="עריכת דוח"
                  aria-label={`עריכת דוח ${e.name}`}
                  className="w-8 h-8 rounded-lg bg-panel2 border border-control text-accent cursor-pointer flex items-center justify-center"
                >
                  <Pencil size={15} />
                </button>
              </div>
            </div>
          )
        })}
      </Card>

      <div className="text-[11.5px] text-dim mt-3">
        לחיצה על עיפרון פותחת את הדוח היומי לעריכת שעות כניסה/יציאה · ייצוא CSV/PDF מתבצע לחודש הנבחר
      </div>

      {month && editEmployee && (
        <AttendanceEditModal
          month={month}
          employee={editEmployee}
          monthLabel={label}
          onPatch={onPatch}
          onClose={() => setEditId(null)}
        />
      )}
    </div>
  )
}
