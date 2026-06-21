'use client'

export interface SortState<K extends string> {
  key: K
  dir: 'asc' | 'desc'
}

interface SortChipsProps<K extends string> {
  fields: { key: K; label: string }[]
  sort: SortState<K>
  onSort: (key: K) => void
}

export function SortChips<K extends string>({ fields, sort, onSort }: SortChipsProps<K>) {
  return (
    <div className="flex items-center gap-[9px] flex-wrap">
      <span className="text-[12.5px] text-faint font-semibold ml-1">מיון:</span>
      {fields.map((f) => {
        const active = sort.key === f.key
        return (
          <button
            key={f.key}
            onClick={() => onSort(f.key)}
            className="inline-flex items-center gap-1 rounded-lg text-[12.5px] font-semibold cursor-pointer"
            style={{
              padding: '7px 12px',
              background: active ? 'rgba(59,130,246,.14)' : 'var(--panel2)',
              color: active ? 'var(--accent)' : 'var(--muted)',
              border: `1px solid ${active ? '#2b4d7a' : 'var(--control)'}`,
            }}
          >
            {f.label}
            <span className="opacity-80">{active ? (sort.dir === 'asc' ? '↑' : '↓') : ''}</span>
          </button>
        )
      })}
    </div>
  )
}

export function nextDir<K extends string>(prev: SortState<K>, key: K): SortState<K> {
  return { key, dir: prev.key === key && prev.dir === 'asc' ? 'desc' : 'asc' }
}
