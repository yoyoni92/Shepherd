'use client'
import { useState } from 'react'
import { X } from 'lucide-react'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

export type FieldType = 'text' | 'number' | 'date' | 'select' | 'tel'

export interface FieldDef {
  key: string
  label: string
  type: FieldType
  required?: boolean
  options?: { value: string; label: string }[] | ((values: FormValues) => { value: string; label: string }[])
  placeholder?: string
  ltr?: boolean
  /** Format check, run only on a non-empty value. Returns a Hebrew error or null. */
  validate?: (v: string) => string | null
}

export type FormValues = Record<string, string>

/** Field-driven add/edit modal. Empty required fields and failed format checks block submit. */
export function EntityFormModal({
  title,
  fields,
  initial,
  submitLabel,
  onSubmit,
  onClose,
}: {
  title: string
  fields: FieldDef[]
  initial?: FormValues
  submitLabel: string
  onSubmit: (values: FormValues) => void
  onClose: () => void
}) {
  const [values, setValues] = useState<FormValues>(() => {
    const v: FormValues = {}
    for (const f of fields) v[f.key] = initial?.[f.key] ?? ''
    return v
  })
  const [errors, setErrors] = useState<Record<string, string>>({})

  const set = (key: string, val: string) => setValues((s) => ({ ...s, [key]: val }))

  const submit = () => {
    const errs: Record<string, string> = {}
    for (const f of fields) {
      const val = (values[f.key] ?? '').trim()
      if (!val) {
        if (f.required) errs[f.key] = 'שדה חובה'
        continue
      }
      const e = f.validate?.(val)
      if (e) errs[f.key] = e
    }
    setErrors(errs)
    if (Object.keys(errs).length === 0) onSubmit(values)
  }

  const inputCls = 'bg-bg border border-control rounded-[8px] text-[13.5px] text-ink outline-none focus:border-accent w-full'

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <div className="flex items-center gap-3 border-b border-line" style={{ padding: '17px 22px' }}>
          <DialogTitle className="text-[16px] font-extrabold flex-1">{title}</DialogTitle>
          <button
            onClick={onClose}
            aria-label="סגור"
            className="w-[34px] h-[34px] rounded-lg bg-panel2 border border-control text-muted cursor-pointer flex items-center justify-center"
          >
            <X size={17} />
          </button>
        </div>

        <div className="overflow-y-auto" style={{ padding: '16px 22px', maxHeight: '60vh' }}>
          <div className="grid grid-cols-2" style={{ gap: '14px 16px' }}>
            {fields.map((f) => (
              <div key={f.key} className={f.type === 'select' || f.key === 'full_name' || f.key === 'licensing_plate' ? 'col-span-2' : ''}>
                <label htmlFor={f.key} className="block text-[12px] font-semibold text-muted mb-[6px]">
                  {f.label}
                  {f.required && <span className="text-danger"> *</span>}
                </label>
                {f.type === 'select' ? (
                  <select
                    id={f.key}
                    value={values[f.key]}
                    onChange={(e) => set(f.key, e.target.value)}
                    className={inputCls}
                    style={{ padding: '9px 10px' }}
                  >
                    <option value="">— בחר/י —</option>
                    {(typeof f.options === 'function' ? f.options(values) : f.options)?.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    id={f.key}
                    type={f.type === 'number' ? 'number' : f.type === 'date' ? 'date' : f.type === 'tel' ? 'tel' : 'text'}
                    value={values[f.key]}
                    placeholder={f.placeholder}
                    onChange={(e) => set(f.key, e.target.value)}
                    className={`${inputCls}${f.ltr ? ' ltr text-left' : ''}`}
                    style={{ padding: '9px 11px' }}
                  />
                )}
                {errors[f.key] && <p className="text-danger text-[11.5px] mt-1">{errors[f.key]}</p>}
              </div>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2.5 border-t border-line" style={{ padding: '15px 22px' }}>
          <Button onClick={submit}>{submitLabel}</Button>
          <Button variant="secondary" onClick={onClose}>
            ביטול
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
