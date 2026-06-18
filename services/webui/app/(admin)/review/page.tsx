'use client'
import { useReviewQueue } from '@/hooks/useReviewQueue'

const ICON: Record<string, string> = {
  output_blocked: '🛡',
  plate_mismatch: '⚠',
  low_confidence: '🖼',
}

export default function ReviewPage() {
  const { items, loading, resolve } = useReviewQueue()
  return (
    <div>
      <h2 className="text-[15px] font-bold mb-4">Review Queue</h2>
      {loading && <p className="text-muted text-sm">Loading...</p>}
      {!loading && items.length === 0 && (
        <p className="text-muted text-sm">No items pending review.</p>
      )}
      <div className="flex flex-col gap-3">
        {items.map(item => (
          <div
            key={item.id}
            className={`bg-panel border border-line rounded-xl p-3.5 flex items-center gap-3.5 border-l-4 ${
              item.reason !== 'low_confidence' ? 'border-l-rose-600' : 'border-l-amber-500'
            }`}
          >
            <div className="w-10 h-10 rounded-lg bg-blue-950 border border-blue-900 flex items-center justify-center text-xl flex-shrink-0">
              {ICON[item.reason] ?? '📄'}
            </div>
            <div className="flex-1 min-w-0">
              <b className="text-[12.5px] block truncate">{item.file_name}</b>
              <p className="text-[11px] text-muted mt-0.5">{item.message}</p>
            </div>
            <button
              onClick={() => resolve({ id: item.id, action: 'accept' })}
              className="bg-emerald-950 text-emerald-300 border border-emerald-800 rounded-lg px-3 py-1.5 font-bold text-[11px] hover:brightness-110 flex-shrink-0"
            >
              Accept
            </button>
            <button
              onClick={() => resolve({ id: item.id, action: 'reject' })}
              className="bg-rose-950 text-rose-300 border border-rose-900 rounded-lg px-3 py-1.5 font-bold text-[11px] hover:brightness-110 flex-shrink-0"
            >
              Reject
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
