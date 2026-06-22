'use client'
import { useState, useRef, useCallback } from 'react'
import { X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import type { UiVehicle, UiDriver, AccidentCreate } from '@/lib/api/schemas'
import { Button } from '@/components/ui/button'

type UploadState =
  | { status: 'idle' }
  | { status: 'uploading' }
  | { status: 'done'; fileUrl: string; fileName: string }
  | { status: 'error' }

const FILE_SLOTS = [
  { category: 'photo_our_vehicle',        label: 'צילום רכבנו',      accept: 'image/*' },
  { category: 'photo_other_vehicle',      label: 'צילום רכב שני',    accept: 'image/*' },
  { category: 'photo_accident_area',      label: 'צילום מקום',       accept: 'image/*' },
  { category: 'another_driver_insurance', label: 'ביטוח נהג שני',    accept: 'image/*,application/pdf' },
  { category: 'another_car_registration', label: 'רישום רכב שני',    accept: 'image/*,application/pdf' },
  { category: 'another_driver_license',   label: 'רישיון נהג שני',   accept: 'image/*,application/pdf' },
  { category: 'accident_video',           label: 'וידאו תאונה',      accept: 'video/*' },
] as const

const emptyUploads = (): Record<string, UploadState> =>
  Object.fromEntries(FILE_SLOTS.map((s) => [s.category, { status: 'idle' }]))

export function AccidentFormModal({
  vehicles,
  drivers,
  onSubmit,
  onClose,
  submitting,
}: {
  vehicles: UiVehicle[]
  drivers: UiDriver[]
  onSubmit: (payload: AccidentCreate) => void
  onClose: () => void
  submitting: boolean
}) {
  const [vehicleId, setVehicleId] = useState('')
  const [driverId, setDriverId] = useState('')
  const [datetime, setDatetime] = useState('')
  const [location, setLocation] = useState('')
  const [description, setDescription] = useState('')
  const [otherPlate, setOtherPlate] = useState('')
  const [otherPhone, setOtherPhone] = useState('')
  const [otherId, setOtherId] = useState('')
  const [uploads, setUploads] = useState<Record<string, UploadState>>(emptyUploads)
  const inputRefs = useRef<Record<string, HTMLInputElement | null>>({})

  const handleFile = useCallback(async (category: string, file: File) => {
    setUploads((u) => ({ ...u, [category]: { status: 'uploading' } }))
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch('/api/accident-upload', { method: 'POST', body: form })
      if (!res.ok) throw new Error('upload failed')
      const { file_url } = await res.json()
      setUploads((u) => ({ ...u, [category]: { status: 'done', fileUrl: file_url, fileName: file.name } }))
    } catch {
      setUploads((u) => ({ ...u, [category]: { status: 'error' } }))
    }
  }, [])

  const anyUploading = Object.values(uploads).some((u) => u.status === 'uploading')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const attachments = FILE_SLOTS
      .filter((s) => uploads[s.category].status === 'done')
      .map((s) => ({
        category: s.category,
        file_url: (uploads[s.category] as { status: 'done'; fileUrl: string }).fileUrl,
      }))
    onSubmit({
      vehicle_id: vehicleId,
      driver_id: driverId || undefined,
      datetime,
      location: location || undefined,
      description: description || undefined,
      another_driver_licensing_plate: otherPlate || undefined,
      another_driver_phone_number: otherPhone || undefined,
      another_driver_id_number: otherId || undefined,
      attachments,
    })
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,.55)' }}
    >
      <div
        className="bg-raised border border-line rounded-2xl w-full overflow-y-auto"
        style={{ maxWidth: 600, maxHeight: '90vh', padding: '24px 26px' }}
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-[17px] font-bold">הוספת תאונה</h2>
          <button onClick={onClose} className="text-faint hover:text-ink">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {/* vehicle */}
          <div>
            <label className="text-[12px] text-faint block mb-1">רכב *</label>
            <select
              value={vehicleId}
              onChange={(e) => setVehicleId(e.target.value)}
              required
              className="w-full bg-panel border border-control rounded-lg text-[13px] font-semibold"
              style={{ padding: '9px 12px' }}
            >
              <option value="">-- בחר רכב --</option>
              {vehicles.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.plate} - {v.make} {v.model}
                </option>
              ))}
            </select>
          </div>

          {/* driver */}
          <div>
            <label className="text-[12px] text-faint block mb-1">נהג</label>
            <select
              value={driverId}
              onChange={(e) => setDriverId(e.target.value)}
              className="w-full bg-panel border border-control rounded-lg text-[13px] font-semibold"
              style={{ padding: '9px 12px' }}
            >
              <option value="">-- ללא נהג --</option>
              {drivers.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          {/* datetime */}
          <div>
            <label className="text-[12px] text-faint block mb-1">תאריך ושעה *</label>
            <input
              type="datetime-local"
              value={datetime}
              onChange={(e) => setDatetime(e.target.value)}
              required
              className="w-full bg-panel border border-control rounded-lg text-[13px] font-semibold ltr"
              style={{ padding: '9px 12px' }}
            />
          </div>

          {/* location */}
          <div>
            <label className="text-[12px] text-faint block mb-1">מיקום</label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full bg-panel border border-control rounded-lg text-[13px] font-semibold"
              style={{ padding: '9px 12px' }}
            />
          </div>

          {/* description */}
          <div>
            <label className="text-[12px] text-faint block mb-1">תיאור</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-panel border border-control rounded-lg text-[13px] font-semibold"
              style={{ padding: '9px 12px' }}
            />
          </div>

          <hr className="border-line" />
          <div className="text-[12px] font-semibold text-muted">פרטי הצד השני</div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[12px] text-faint block mb-1">לוחית</label>
              <input
                type="text"
                value={otherPlate}
                onChange={(e) => setOtherPlate(e.target.value)}
                className="w-full bg-panel border border-control rounded-lg text-[13px] font-semibold ltr"
                style={{ padding: '9px 12px' }}
              />
            </div>
            <div>
              <label className="text-[12px] text-faint block mb-1">טלפון</label>
              <input
                type="text"
                value={otherPhone}
                onChange={(e) => setOtherPhone(e.target.value)}
                className="w-full bg-panel border border-control rounded-lg text-[13px] font-semibold ltr"
                style={{ padding: '9px 12px' }}
              />
            </div>
            <div>
              <label className="text-[12px] text-faint block mb-1">ת.ז.</label>
              <input
                type="text"
                value={otherId}
                onChange={(e) => setOtherId(e.target.value)}
                className="w-full bg-panel border border-control rounded-lg text-[13px] font-semibold"
                style={{ padding: '9px 12px' }}
              />
            </div>
          </div>

          <hr className="border-line" />
          <div className="text-[12px] font-semibold text-muted">קבצים מצורפים (אופציונלי)</div>

          <div className="flex flex-col gap-2">
            {FILE_SLOTS.map((slot) => {
              const state = uploads[slot.category]
              return (
                <div key={slot.category}>
                  <div className="text-[11px] text-faint mb-1">{slot.label}</div>
                  <div
                    className="border border-dashed border-control rounded-lg text-center text-[12px] text-faint cursor-pointer hover:border-[#2b3550] relative"
                    style={{ padding: '10px 14px' }}
                    onClick={() => inputRefs.current[slot.category]?.click()}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => {
                      e.preventDefault()
                      const f = e.dataTransfer.files[0]
                      if (f) handleFile(slot.category, f)
                    }}
                  >
                    {state.status === 'idle' && (
                      <span>
                        גרור או <b>בחר קובץ</b>
                      </span>
                    )}
                    {state.status === 'uploading' && (
                      <span className="flex items-center justify-center gap-1">
                        <Loader2 size={13} className="animate-spin" />
                        מעלה...
                      </span>
                    )}
                    {state.status === 'done' && (
                      <span className="flex items-center justify-center gap-1 text-emerald-400">
                        <CheckCircle size={13} />
                        {(state as { fileName: string }).fileName}
                      </span>
                    )}
                    {state.status === 'error' && (
                      <span className="flex items-center justify-center gap-1 text-amber-400">
                        <AlertCircle size={13} />
                        שגיאה - נסה שוב
                      </span>
                    )}
                    <input
                      ref={(el) => { inputRefs.current[slot.category] = el }}
                      type="file"
                      accept={slot.accept}
                      className="hidden"
                      onChange={(e) => {
                        const f = e.target.files?.[0]
                        if (f) handleFile(slot.category, f)
                      }}
                    />
                  </div>
                </div>
              )
            })}
          </div>

          <div className="flex gap-2 pt-2">
            <Button
              type="submit"
              className="flex-1"
              disabled={submitting || anyUploading}
            >
              {submitting ? 'שומר...' : 'הוסף תאונה'}
            </Button>
            <Button type="button" variant="secondary" onClick={onClose}>
              ביטול
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
