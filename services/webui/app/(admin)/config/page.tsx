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
