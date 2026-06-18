'use client'
import { useConfig } from '@/hooks/useConfig'
import { useState } from 'react'

export default function ConfigPage() {
  const { config, loading, save, saving } = useConfig()
  const [edits, setEdits] = useState<Record<string, string>>({})

  if (loading) return <p className="text-muted text-sm">Loading...</p>

  return (
    <div>
      <h2 className="text-[15px] font-bold mb-4">Config</h2>
      <div className="bg-panel border border-line rounded-xl p-4">
        <h3 className="text-[11px] uppercase tracking-wider text-slate-400 mb-3">
          System configuration
        </h3>
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="text-muted text-[10px] uppercase tracking-wider">
              <th className="text-left py-2 px-2">Key</th>
              <th className="text-left py-2 px-2">Value</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(config ?? {}).map(([key, val]) => (
              <tr key={key} className="border-t border-line">
                <td className="py-2 px-2 font-mono text-slate-300">{key}</td>
                <td className="py-2 px-2">
                  <input
                    className="bg-panel2 border border-line rounded px-2 py-1 text-slate-200 font-mono text-xs w-40 outline-none focus:border-blue-500"
                    defaultValue={String(val)}
                    onChange={e => setEdits(d => ({ ...d, [key]: e.target.value }))}
                  />
                </td>
                <td className="py-2 px-2">
                  <button
                    disabled={saving}
                    onClick={() => save({ key, value: edits[key] ?? val })}
                    className="bg-emerald-950 text-emerald-300 border border-emerald-800 rounded px-3 py-1 font-bold text-[11px] hover:brightness-110 disabled:opacity-50"
                  >
                    Save
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
