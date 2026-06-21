export const UNASSIGNED = 'לא משויך'

/** Two-letter initials from a Hebrew/Latin name; em-dash for empty/unassigned. */
export function initials(name: string): string {
  if (!name || name === UNASSIGNED) return '—'
  const parts = name.trim().split(/\s+/)
  return (parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')
}

const AVATAR_PALETTE: [string, string][] = [
  ['#6366f1', '#4338ca'],
  ['#0891b2', '#0e7490'],
  ['#16a34a', '#15803d'],
  ['#db2777', '#9d174d'],
  ['#d97706', '#b45309'],
  ['#7c3aed', '#5b21b6'],
]

/** Deterministic gradient stops keyed by id (6-colour palette). */
export function avatarColor(id: number): [string, string] {
  return AVATAR_PALETTE[id % AVATAR_PALETTE.length]
}

/** Whole days from `today` until `dateStr` (negative = past). */
export function daysTo(dateStr: string, today: Date = new Date()): number {
  const target = new Date(dateStr).getTime()
  const base = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime()
  return Math.round((target - base) / 86_400_000)
}

/** ISO date -> DD/MM/YYYY (LTR-rendered). */
export function fmtDate(dateStr: string): string {
  const x = new Date(dateStr)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(x.getDate())}/${p(x.getMonth() + 1)}/${x.getFullYear()}`
}

/** ISO datetime -> DD/MM/YYYY HH:MM (local time, LTR-rendered). */
export function fmtDateTime(dateStr: string): string {
  const d = new Date(dateStr)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`
}

/** Generic immutable sort: case-insensitive for strings, dir asc/desc. */
export function sortItems<T>(
  items: readonly T[],
  accessor: (item: T) => string | number,
  dir: 'asc' | 'desc',
): T[] {
  const mul = dir === 'asc' ? 1 : -1
  return [...items].sort((a, b) => {
    let x = accessor(a)
    let y = accessor(b)
    if (typeof x === 'string' && typeof y === 'string') {
      x = x.toLowerCase()
      y = y.toLowerCase()
    }
    return (x < y ? -1 : x > y ? 1 : 0) * mul
  })
}
