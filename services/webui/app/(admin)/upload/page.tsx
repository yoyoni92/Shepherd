'use client'
import { useState, useRef } from 'react'
import { uploadDocument } from '@/lib/api/gateway'
import type { UploadResult } from '@/lib/api/schemas'

interface UploadRow extends UploadResult { file: string }

export default function UploadPage() {
  const [uploads, setUploads] = useState<UploadRow[]>([])
  const [uploading, setUploading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleFiles(files: FileList | null) {
    if (!files?.length) return
    setUploading(true)
    for (const file of Array.from(files)) {
      try {
        const res = await uploadDocument(file)
        setUploads(u => [...u, { file: file.name, ...res }])
      } catch {
        setUploads(u => [...u, { file: file.name, doc_type: 'error', confidence: 0, status: 'upload failed', flagged: true }])
      }
    }
    setUploading(false)
  }

  return (
    <div>
      <h2 className="text-[15px] font-bold mb-4">Upload</h2>
      <div
        className="border-2 border-dashed border-slate-700 rounded-xl p-8 text-center text-slate-400 bg-panel2 cursor-pointer hover:border-slate-500"
        onClick={() => inputRef.current?.click()}
        onDragOver={e => e.preventDefault()}
        onDrop={e => { e.preventDefault(); handleFiles(e.dataTransfer.files) }}
      >
        <div className="text-3xl mb-1.5">&#x2B06;</div>
        Drag a document here, or <b>browse</b>
        <div className="text-muted text-xs mt-1">
          insurance certificate &middot; annual license (&#x05E8;&#x05D9;&#x05E9;&#x05D5;&#x05D9;) &middot; traffic ticket (&#x05D3;&#x05D5;&#x05D7;) &middot; vehicle photo &middot; PDF/JPG/PNG
        </div>
      </div>
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept=".pdf,.jpg,.jpeg,.png"
        multiple
        onChange={e => handleFiles(e.target.files)}
      />
      {uploading && <p className="text-xs text-muted mt-2">Uploading...</p>}
      {uploads.length > 0 && (
        <div className="bg-panel border border-line rounded-xl p-4 mt-4">
          <h3 className="text-[11px] uppercase tracking-wider text-slate-400 mb-3">Recent uploads</h3>
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="text-muted text-[10px] uppercase tracking-wider">
                <th className="text-left py-2 px-2">File</th>
                <th className="text-left py-2 px-2">Type</th>
                <th className="text-left py-2 px-2">Conf.</th>
                <th className="text-left py-2 px-2">Result</th>
              </tr>
            </thead>
            <tbody>
              {uploads.map((u, i) => (
                <tr key={i} className="border-t border-line">
                  <td className="py-2 px-2">{u.file}</td>
                  <td className="py-2 px-2">{u.doc_type}</td>
                  <td className="py-2 px-2">{u.confidence.toFixed(2)}</td>
                  <td className="py-2 px-2">
                    <span className={`text-[9.5px] font-bold px-2 py-0.5 rounded-full ${
                      u.flagged
                        ? 'bg-amber-950 text-amber-300 border border-amber-700'
                        : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                    }`}>
                      {u.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
