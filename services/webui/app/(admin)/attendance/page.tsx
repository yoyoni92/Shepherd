'use client'
import { useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight, Download, FileText, Pencil } from 'lucide-react'
import { useAttendance } from '@/hooks/useAttendance'
import { useAttendanceSettings } from '@/hooks/useAttendanceSettings'
import { aggregate, summarize, employeeStatus, buildCsv, monthOptions, type AttendanceDay } from '@/lib/attendance'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Avatar } from '@/components/Avatar'
import { ATT_STATUS_META, HOLIDAY_META } from '@/components/meta'
import { AttendanceEditModal } from '@/components/AttendanceEditModal'

const GRID = '2fr 88px 116px 116px 86px 78px 108px 64px'
const MONTHS = monthOptions(3)

const timeFieldStyle = {
  background: 'var(--panel-2, #0f172a)',
  color: 'var(--accent, #60a5fa)',
  border: '1px solid var(--line)',
} as const

const WEEKDAYS = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת']

// הגדרות tab: the company-scoped clock-in window + working-day rules (relocated in Feature 7).
function AttendanceConfigPanel() {
  const { settings, loading, save } = useAttendanceSettings()
  const [enabled, setEnabled] = useState(false)
  const [start, setStart] = useState('07:00')
  const [end, setEnd] = useState('17:00')
  const [workDays, setWorkDays] = useState<number[]>([0, 1, 2, 3, 4])
  const [chagWorking, setChagWorking] = useState(false)
  const [erevChagWorking, setErevChagWorking] = useState(true)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [ok, setOk] = useState(false)

  useEffect(() => {
    if (!settings) return
    setEnabled(settings.enabled)
    setStart(settings.start || '07:00')
    setEnd(settings.end || '17:00')
    setWorkDays(settings.work_days ?? [0, 1, 2, 3, 4])
    setChagWorking(settings.chag_working ?? false)
    setErevChagWorking(settings.erev_chag_working ?? true)
  }, [settings])

  const toggleDay = (d: number) => {
    setOk(false)
    setWorkDays((prev) => (prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d].sort((a, b) => a - b)))
  }

  const submit = async () => {
    setErr(null)
    setOk(false)
    setBusy(true)
    try {
      await save({
        enabled,
        start,
        end,
        work_days: workDays,
        chag_working: chagWorking,
        erev_chag_working: erevChagWorking,
      })
      setOk(true)
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'שמירת ההגדרות נכשלה')
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <p className="text-faint text-sm">טוען…</p>

  return (
    <Card style={{ padding: '8px 22px 16px', maxWidth: 620 }}>
      <div className="flex items-center gap-5 border-b border-divider" style={{ padding: '18px 0' }}>
        <div className="flex-1 min-w-0">
          <div className="text-[14.5px] font-bold mb-[3px]">חלון דיווח נוכחות</div>
          <div className="text-[12px] text-faint">
            כאשר מופעל, דיווח כניסה/יציאה דרך הבוט ייחסם מחוץ לטווח השעות. כבוי = כל שעה מותרת.
          </div>
        </div>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => {
              setEnabled(e.target.checked)
              setOk(false)
            }}
            style={{ width: 16, height: 16 }}
          />
          <span className="text-[13px]">{enabled ? 'מופעל' : 'כבוי'}</span>
        </label>
      </div>

      <div className="flex items-center gap-5 border-b border-divider" style={{ padding: '18px 0', opacity: enabled ? 1 : 0.5 }}>
        <div className="flex-1 text-[13px] text-faint">טווח שעות מותר</div>
        <div className="flex items-center gap-2">
          <input
            type="time"
            value={start}
            disabled={!enabled}
            onChange={(e) => {
              setStart(e.target.value)
              setOk(false)
            }}
            className="ltr rounded-lg text-[14px]"
            style={{ ...timeFieldStyle, padding: '6px 8px' }}
          />
          <span className="text-faint">-</span>
          <input
            type="time"
            value={end}
            disabled={!enabled}
            onChange={(e) => {
              setEnd(e.target.value)
              setOk(false)
            }}
            className="ltr rounded-lg text-[14px]"
            style={{ ...timeFieldStyle, padding: '6px 8px' }}
          />
        </div>
      </div>

      <div className="border-b border-divider" style={{ padding: '18px 0' }}>
        <div className="text-[14.5px] font-bold mb-[3px]">ימי עבודה</div>
        <div className="text-[12px] text-faint mb-[12px]">
          ימים שאינם מסומנים (כולל שבת) לא נספרים כהיעדרות בדוח החודשי.
        </div>
        <div className="flex flex-wrap gap-2">
          {WEEKDAYS.map((name, d) => {
            const on = workDays.includes(d)
            return (
              <button
                key={d}
                onClick={() => toggleDay(d)}
                className="text-[12.5px] font-bold rounded-lg border cursor-pointer"
                style={{
                  padding: '7px 13px',
                  color: on ? 'var(--accent, #60a5fa)' : 'var(--muted, #94a3b8)',
                  background: on ? 'rgba(96,165,250,.12)' : 'var(--panel-2, #0f172a)',
                  borderColor: on ? 'var(--accent, #60a5fa)' : 'var(--line)',
                }}
              >
                {name}
              </button>
            )
          })}
        </div>
      </div>

      <div className="flex items-center gap-5 border-b border-divider" style={{ padding: '18px 0' }}>
        <div className="flex-1 min-w-0">
          <div className="text-[14.5px] font-bold mb-[3px]">חג (יום טוב)</div>
          <div className="text-[12px] text-faint">כבוי = ימי חג אינם ימי עבודה ולא נספרים בדוח.</div>
        </div>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={chagWorking}
            onChange={(e) => {
              setChagWorking(e.target.checked)
              setOk(false)
            }}
            style={{ width: 16, height: 16 }}
          />
          <span className="text-[13px]">{chagWorking ? 'יום עבודה' : 'יום מנוחה'}</span>
        </label>
      </div>

      <div className="flex items-center gap-5" style={{ padding: '18px 0' }}>
        <div className="flex-1 min-w-0">
          <div className="text-[14.5px] font-bold mb-[3px]">ערב חג</div>
          <div className="text-[12px] text-faint">מופעל = ערבי חג נחשבים ימי עבודה רגילים.</div>
        </div>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={erevChagWorking}
            onChange={(e) => {
              setErevChagWorking(e.target.checked)
              setOk(false)
            }}
            style={{ width: 16, height: 16 }}
          />
          <span className="text-[13px]">{erevChagWorking ? 'יום עבודה' : 'יום מנוחה'}</span>
        </label>
      </div>

      {err && <p className="text-[12px] pt-3" style={{ color: '#f87171' }}>{err}</p>}
      {ok && <p className="text-[12px] pt-3" style={{ color: '#86efac' }}>ההגדרות נשמרו ✓</p>}

      <div className="flex justify-start pt-[18px]">
        <Button onClick={submit} disabled={busy}>
          {busy ? 'שומר…' : 'שמירת הגדרות'}
        </Button>
      </div>
    </Card>
  )
}

export default function AttendancePage() {
  return (
    <Tabs defaultValue="records" className="animate-fade-up">
      <TabsList className="mb-[18px]">
        <TabsTrigger value="records">נוכחות</TabsTrigger>
        <TabsTrigger value="config">הגדרות</TabsTrigger>
      </TabsList>

      <TabsContent value="records">
        <AttendanceRecords />
      </TabsContent>

      <TabsContent value="config">
        <AttendanceConfigPanel />
      </TabsContent>
    </Tabs>
  )
}

function AttendanceRecords() {
  const [idx, setIdx] = useState(MONTHS.length - 1)
  const [editId, setEditId] = useState<string | null>(null)
  const current = MONTHS[idx]
  const { month, holidays, loading, patchDay } = useAttendance(current.key)

  const label = month?.label ?? current.label
  const employees = month?.employees ?? []
  const records = month?.records ?? {}
  const summary = summarize(employees, records)

  const onPatch = (employeeId: string, day: number, patch: Partial<AttendanceDay>) =>
    patchDay({ employeeId, day, patch })

  const exportCsv = () => {
    const csv = buildCsv(employees, records, holidays)
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
    <div>
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

      {holidays.length > 0 && (
        <Card className="rounded-[13px] mb-[18px]" style={{ padding: '14px 18px' }}>
          <div className="text-[12.5px] font-bold text-faint mb-[10px]">חגי ומועדי החודש</div>
          <div className="flex flex-wrap gap-2">
            {holidays.map((h) => {
              const c = HOLIDAY_META[h.kind]
              return (
                <span
                  key={`${h.day}-${h.name}`}
                  className="text-[11.5px] font-bold rounded-md inline-flex items-center gap-[6px] whitespace-nowrap"
                  style={{ color: c.color, background: c.bg, padding: '4px 10px' }}
                >
                  <span className="ltr opacity-80">{h.dateLabel}</span>
                  {h.name}
                </span>
              )
            })}
          </div>
        </Card>
      )}

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
