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
}

const FIELDS: Field[] = [
  { key: 'docs_expiry_warning_days', label: 'התראת תוקף מסמכים', desc: 'מספר ימים מראש להתראה על מסמך פג', unit: 'ימים', step: 5 },
  { key: 'condition_min_alert', label: 'סף מצב רכב מינימלי', desc: 'מתחת לציון זה הרכב מסומן לתחזוקה', unit: 'נק׳', step: 5 },
  { key: 'ticket_unpaid_days', label: 'חלון דוחות לא משולמים', desc: 'ימים עד שדוח מסומן כחורג', unit: 'ימים', step: 1 },
  { key: 'maintenance_interval_km', label: 'מרווח טיפול (ק״מ)', desc: 'מרחק בין טיפולים תקופתיים', unit: 'ק״מ', step: 1000 },
  { key: 'maintenance_interval_days', label: 'מרווח טיפול (זמן)', desc: 'ימים מקסימלי בין טיפולים', unit: 'ימים', step: 30 },
  { key: 'low_confidence_threshold', label: 'סף ביטחון לחילוץ', desc: 'מתחת לאחוז זה פריט עובר לתור בדיקה', unit: '%', step: 5 },
]

const DEFAULTS: Record<string, number> = {
  docs_expiry_warning_days: 30,
  condition_min_alert: 60,
  ticket_unpaid_days: 14,
  maintenance_interval_km: 15000,
  maintenance_interval_days: 180,
  low_confidence_threshold: 70,
}

function seed(config: Record<string, unknown> | undefined): Record<string, number> {
  const out: Record<string, number> = {}
  for (const f of FIELDS) out[f.key] = Number(config?.[f.key] ?? DEFAULTS[f.key])
  return out
}

export default function ConfigPage() {
  const { config, loading, save, saving } = useConfig()
  const [values, setValues] = useState<Record<string, number>>(() => seed(undefined))

  useEffect(() => {
    if (config) setValues(seed(config))
  }, [config])

  if (loading) return <p className="text-faint text-sm">טוען…</p>

  const bump = (key: string, delta: number) =>
    setValues((v) => ({ ...v, [key]: Math.max(0, v[key] + delta) }))

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
              <div className="text-[11px] font-mono mt-1 ltr" style={{ color: '#334155' }}>
                {f.key}
              </div>
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
    </div>
  )
}
