'use client'
import { useEffect, useState } from 'react'
import { useConfig } from '@/hooks/useConfig'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

interface Field {
  key: string
  label: string
  desc: string
  unit: string
  step: number
  max?: number
}

// Real seeded system_config numeric keys (services/fleet-api, db seed).
const FIELDS: Field[] = [
  { key: 'license_expiring_days', label: 'התראת תוקף רישוי', desc: 'ימים מראש להתראה על רישוי רכב פג', unit: 'ימים', step: 1 },
  { key: 'insurance_expiring_days', label: 'התראת תוקף ביטוח', desc: 'ימים מראש להתראה על ביטוח פג', unit: 'ימים', step: 1 },
  { key: 'maintenance_km_buffer', label: 'מרווח התראת טיפול', desc: 'ק״מ לפני הטיפול הבא שבו מופקת התראה', unit: 'ק״מ', step: 100 },
  { key: 'image_confidence_min', label: 'סף ביטחון לזיהוי מסמך', desc: 'מתחת לערך זה (0–1) מסמך עובר לבדיקה', unit: '', step: 0.05, max: 1 },
]

const DEFAULTS: Record<string, number> = {
  license_expiring_days: 30,
  insurance_expiring_days: 30,
  maintenance_km_buffer: 1000,
  image_confidence_min: 0.7,
}

function seed(config: Record<string, unknown> | undefined): Record<string, number> {
  const out: Record<string, number> = {}
  for (const f of FIELDS) out[f.key] = Number(config?.[f.key] ?? DEFAULTS[f.key])
  return out
}

function AttendanceWindowCard() {
  const { config, save, saving } = useConfig()
  const [enabled, setEnabled] = useState(false)
  const [start, setStart] = useState('07:00')
  const [end, setEnd] = useState('17:00')

  useEffect(() => {
    if (!config) return
    const e = config['attendance_window_enabled']
    setEnabled(e === true || e === 'true')
    if (config['attendance_window_start']) setStart(String(config['attendance_window_start']))
    if (config['attendance_window_end']) setEnd(String(config['attendance_window_end']))
  }, [config])

  const saveAll = () => {
    save({ key: 'attendance_window_enabled', value: enabled })
    save({ key: 'attendance_window_start', value: start })
    save({ key: 'attendance_window_end', value: end })
  }

  return (
    <Card style={{ padding: '8px 22px 16px', marginTop: 18 }}>
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
            onChange={(e) => setEnabled(e.target.checked)}
            style={{ width: 16, height: 16 }}
          />
          <span className="text-[13px]">{enabled ? 'מופעל' : 'כבוי'}</span>
        </label>
      </div>
      <div className="flex items-center gap-5" style={{ padding: '18px 0', opacity: enabled ? 1 : 0.5 }}>
        <div className="flex-1 text-[13px] text-faint">טווח שעות מותר</div>
        <div className="flex items-center gap-2">
          <input
            type="time"
            value={start}
            disabled={!enabled}
            onChange={(e) => setStart(e.target.value)}
            className="ltr bg-bg border border-control rounded-lg text-[14px] text-accent"
            style={{ padding: '6px 8px' }}
          />
          <span className="text-faint">—</span>
          <input
            type="time"
            value={end}
            disabled={!enabled}
            onChange={(e) => setEnd(e.target.value)}
            className="ltr bg-bg border border-control rounded-lg text-[14px] text-accent"
            style={{ padding: '6px 8px' }}
          />
        </div>
      </div>
      <div className="flex justify-start pt-[18px]">
        <Button onClick={saveAll} disabled={saving}>
          שמירת חלון דיווח
        </Button>
      </div>
    </Card>
  )
}

export default function ConfigPage() {
  const { config, loading, save, saving } = useConfig()
  const [values, setValues] = useState<Record<string, number>>(() => seed(undefined))

  useEffect(() => {
    if (config) setValues(seed(config))
  }, [config])

  if (loading) return <p className="text-faint text-sm">טוען…</p>

  const bump = (key: string, delta: number) =>
    setValues((v) => {
      const f = FIELDS.find((x) => x.key === key)
      // round to 2dp so 0.05 steps don't drift (image_confidence_min is a 0–1 float)
      let next = Math.max(0, Math.round((v[key] + delta) * 100) / 100)
      if (f?.max != null) next = Math.min(f.max, next)
      return { ...v, [key]: next }
    })

  const saveAll = () => {
    for (const f of FIELDS) save({ key: f.key, value: values[f.key] })
  }

  return (
    <div className="animate-fade-up" style={{ maxWidth: 760 }}>
      <Card style={{ padding: '8px 22px 16px' }}>
        {FIELDS.map((f) => (
          <div key={f.key} className="flex items-center gap-5 border-b border-divider" style={{ padding: '18px 0' }}>
            <div className="flex-1 min-w-0">
              <div className="text-[14.5px] font-bold mb-[3px]">{f.label}</div>
              <div className="text-[12px] text-faint">{f.desc}</div>
            </div>
            <div className="flex items-center gap-2.5">
              <button
                aria-label={`הפחת ${f.label}`}
                onClick={() => bump(f.key, -f.step)}
                className="w-8 h-8 rounded-lg bg-panel2 border border-control text-muted text-lg cursor-pointer flex items-center justify-center hover:text-ink"
              >
                −
              </button>
              <div className="text-center bg-bg border border-control rounded-lg" style={{ minWidth: 92, padding: '8px 6px' }}>
                <span className="text-[16px] font-extrabold text-accent">{values[f.key].toLocaleString()}</span>
                <span className="text-[11px] text-faint mr-1">{f.unit}</span>
              </div>
              <button
                aria-label={`הגדל ${f.label}`}
                onClick={() => bump(f.key, f.step)}
                className="w-8 h-8 rounded-lg bg-panel2 border border-control text-muted text-lg cursor-pointer flex items-center justify-center hover:text-ink"
              >
                +
              </button>
            </div>
          </div>
        ))}
        <div className="flex justify-start gap-2.5 pt-[18px]">
          <Button onClick={saveAll} disabled={saving}>
            שמירת הגדרות
          </Button>
          <Button variant="secondary" onClick={() => setValues(seed(config))}>
            איפוס
          </Button>
        </div>
      </Card>
      <AttendanceWindowCard />
    </div>
  )
}
