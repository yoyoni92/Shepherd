'use client'
import { useState, useRef } from 'react'
import { uploadDocument } from '@/lib/api/gateway'

interface UploadRow {
  file: string
  ok: boolean
}

// The admin uploads on behalf of the office line; the gateway routes by phone.
const ADMIN_PHONE = process.env.NEXT_PUBLIC_ADMIN_PHONE ?? 'admin'

export default function UploadPage() {
  const [uploads, setUploads] = useState<UploadRow[]>([])
  const [uploading, setUploading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleFiles(files: FileList | null) {
    if (!files?.length) return
    setUploading(true)
    for (const file of Array.from(files)) {
      try {
        const res = await uploadDocument(file, ADMIN_PHONE)
        setUploads((u) => [...u, { file: file.name, ok: res.ok }])
      } catch {
        setUploads((u) => [...u, { file: file.name, ok: false }])
      }
    }
    setUploading(false)
  }

  return (
    <div className="animate-fade-up" style={{ maxWidth: 760 }}>
      <div
        className="border-2 border-dashed border-control rounded-xl p-8 text-center text-muted bg-panel2 cursor-pointer hover:border-[#2b3550]"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault()
          handleFiles(e.dataTransfer.files)
        }}
      >
        <div className="text-3xl mb-1.5">&#x2B06;</div>
        גרור מסמך לכאן, או <b>בחר קובץ</b>
        <div className="text-faint text-xs mt-1">
          ביטוח · רישיון שנתי · דוח תנועה · תמונת רכב · PDF/JPG/PNG
        </div>
      </div>
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept=".pdf,.jpg,.jpeg,.png"
        multiple
        onChange={(e) => handleFiles(e.target.files)}
      />
      {uploading && <p className="text-xs text-faint mt-2">מעלה…</p>}
      {uploads.length > 0 && (
        <div className="bg-panel border border-line rounded-xl p-4 mt-4">
          <h3 className="text-[11px] uppercase tracking-wider text-muted mb-3">העלאות אחרונות</h3>
          <ul className="flex flex-col gap-2">
            {uploads.map((u, i) => (
              <li key={i} className="flex items-center justify-between text-[13px] border-t border-divider pt-2">
                <span className="ltr">{u.file}</span>
                <span
                  className={`text-[10.5px] font-bold px-2 py-0.5 rounded-full ${
                    u.ok
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      : 'bg-amber-950 text-amber-300 border border-amber-700'
                  }`}
                >
                  {u.ok ? 'נשלח לעיבוד' : 'נכשל'}
                </span>
              </li>
            ))}
          </ul>
          <p className="text-[11px] text-dim mt-3">
            הקליטה אסינכרונית — תוצאת הסיווג/חילוץ אינה מוחזרת מיידית; היא תופיע במסך האירועים.
          </p>
        </div>
      )}
    </div>
  )
}
