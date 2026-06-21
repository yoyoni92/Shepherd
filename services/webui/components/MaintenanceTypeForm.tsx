'use client'
import { useState } from 'react'
import { X, Plus, Trash2, ChevronUp, ChevronDown } from 'lucide-react'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import type { UiMaintenanceType, MaintenanceTypeCreate } from '@/lib/api/schemas'

export function MaintenanceTypeForm({
  initial,
  onSubmit,
  onClose,
}: {
  initial?: UiMaintenanceType
  onSubmit: (payload: MaintenanceTypeCreate) => void
  onClose: () => void
}) {
  const [name, setName] = useState(initial?.name ?? '')
  const [description, setDescription] = useState(initial?.description ?? '')
  const [intervalKm, setIntervalKm] = useState(initial ? String(initial.intervalKm) : '')
  const [steps, setSteps] = useState<string[]>(initial?.steps.length ? [...initial.steps] : [''])
  const [error, setError] = useState<string | null>(null)

  const setStep = (i: number, v: string) => setSteps((s) => s.map((x, j) => (j === i ? v : x)))
  const addStep = () => setSteps((s) => [...s, ''])
  const removeStep = (i: number) => setSteps((s) => (s.length > 1 ? s.filter((_, j) => j !== i) : s))
  const move = (i: number, dir: -1 | 1) =>
    setSteps((s) => {
      const j = i + dir
      if (j < 0 || j >= s.length) return s
      const c = [...s]
      ;[c[i], c[j]] = [c[j], c[i]]
      return c
    })

  const submit = () => {
    const cleanSteps = steps.map((s) => s.trim()).filter(Boolean)
    const km = Number(intervalKm)
    if (!name.trim()) return setError('שם חובה')
    if (!intervalKm.trim() || !Number.isInteger(km) || km <= 0) return setError('מרווח ק״מ חייב להיות מספר שלם חיובי')
    if (cleanSteps.length === 0) return setError('יש להגדיר לפחות שלב טיפול אחד')
    if (new Set(cleanSteps).size !== cleanSteps.length) return setError('שמות השלבים חייבים להיות ייחודיים')
    setError(null)
    onSubmit({ name: name.trim(), description: description.trim() || undefined, interval_km: km, steps: cleanSteps })
  }

  const inputCls = 'bg-bg border border-control rounded-[8px] text-[13.5px] text-ink outline-none focus:border-accent w-full'

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <div className="flex items-center gap-3 border-b border-line" style={{ padding: '17px 22px' }}>
          <DialogTitle className="text-[16px] font-extrabold flex-1">
            {initial ? 'עריכת סוג טיפול' : 'הוספת סוג טיפול'}
          </DialogTitle>
          <button
            onClick={onClose}
            aria-label="סגור"
            className="w-[34px] h-[34px] rounded-lg bg-panel2 border border-control text-muted cursor-pointer flex items-center justify-center"
          >
            <X size={17} />
          </button>
        </div>

        <div className="overflow-y-auto" style={{ padding: '16px 22px', maxHeight: '62vh' }}>
          <label className="block text-[12px] font-semibold text-muted mb-[6px]">
            שם הסוג<span className="text-danger"> *</span>
          </label>
          <input value={name} onChange={(e) => setName(e.target.value)} className={inputCls} style={{ padding: '9px 11px' }} />

          <label className="block text-[12px] font-semibold text-muted mb-[6px] mt-4">תיאור</label>
          <input value={description} onChange={(e) => setDescription(e.target.value)} className={inputCls} style={{ padding: '9px 11px' }} />

          <label className="block text-[12px] font-semibold text-muted mb-[6px] mt-4">
            מרווח ק״מ בין טיפולים<span className="text-danger"> *</span>
          </label>
          <input
            type="number"
            value={intervalKm}
            onChange={(e) => setIntervalKm(e.target.value)}
            className={`${inputCls} ltr text-left`}
            style={{ padding: '9px 11px' }}
          />

          <div className="flex items-center justify-between mt-5 mb-2">
            <label className="text-[12px] font-semibold text-muted">
              שלבי הטיפול (לפי הסדר)<span className="text-danger"> *</span>
            </label>
            <button onClick={addStep} className="flex items-center gap-1 text-[12px] text-accent font-semibold cursor-pointer">
              <Plus size={14} />
              הוסף שלב
            </button>
          </div>
          <div className="flex flex-col gap-2">
            {steps.map((s, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="text-[11px] text-faint" style={{ minWidth: 18 }}>
                  {i + 1}.
                </span>
                <input
                  value={s}
                  onChange={(e) => setStep(i, e.target.value)}
                  placeholder="למשל: קטן"
                  className={inputCls}
                  style={{ padding: '8px 10px' }}
                />
                <button onClick={() => move(i, -1)} aria-label="הזז למעלה" className="text-muted hover:text-ink cursor-pointer" disabled={i === 0}>
                  <ChevronUp size={16} style={{ opacity: i === 0 ? 0.3 : 1 }} />
                </button>
                <button onClick={() => move(i, 1)} aria-label="הזז למטה" className="text-muted hover:text-ink cursor-pointer" disabled={i === steps.length - 1}>
                  <ChevronDown size={16} style={{ opacity: i === steps.length - 1 ? 0.3 : 1 }} />
                </button>
                <button onClick={() => removeStep(i)} aria-label="הסר שלב" className="text-danger cursor-pointer" disabled={steps.length === 1}>
                  <Trash2 size={15} style={{ opacity: steps.length === 1 ? 0.3 : 1 }} />
                </button>
              </div>
            ))}
          </div>

          {error && <p className="text-danger text-[12px] mt-3">{error}</p>}
        </div>

        <div className="flex items-center gap-2.5 border-t border-line" style={{ padding: '15px 22px' }}>
          <Button onClick={submit}>{initial ? 'שמירה' : 'הוסף'}</Button>
          <Button variant="secondary" onClick={onClose}>
            ביטול
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
