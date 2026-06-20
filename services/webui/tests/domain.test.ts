import { describe, it, expect } from 'vitest'
import { initials, avatarColor, daysTo, fmtDate, sortItems } from '@/lib/domain'

const TODAY = new Date('2026-06-19T00:00:00')

describe('initials', () => {
  it('takes first letter of first two words', () => {
    expect(initials('דנה לוי')).toBe('דל')
  })
  it('handles single-word names', () => {
    expect(initials('נעם')).toBe('נ')
  })
  it('returns em-dash for empty or unassigned', () => {
    expect(initials('')).toBe('—')
    expect(initials('לא משויך')).toBe('—')
  })
})

describe('avatarColor', () => {
  it('is deterministic and wraps the 6-colour palette', () => {
    expect(avatarColor(1)).toEqual(avatarColor(7))
    expect(avatarColor(0)).toHaveLength(2)
  })
})

describe('daysTo', () => {
  it('counts whole days to a future date', () => {
    expect(daysTo('2026-06-29', TODAY)).toBe(10)
  })
  it('is zero for today and negative for the past', () => {
    expect(daysTo('2026-06-19', TODAY)).toBe(0)
    expect(daysTo('2026-06-09', TODAY)).toBe(-10)
  })
})

describe('fmtDate', () => {
  it('formats ISO dates as DD/MM/YYYY', () => {
    expect(fmtDate('2026-09-02')).toBe('02/09/2026')
  })
})

describe('sortItems', () => {
  const rows = [{ n: 'Beta' }, { n: 'alpha' }, { n: 'Gamma' }]
  it('sorts ascending, case-insensitive, without mutating', () => {
    const out = sortItems(rows, (r) => r.n, 'asc')
    expect(out.map((r) => r.n)).toEqual(['alpha', 'Beta', 'Gamma'])
    expect(rows[0].n).toBe('Beta')
  })
  it('sorts descending', () => {
    expect(sortItems(rows, (r) => r.n, 'desc').map((r) => r.n)).toEqual(['Gamma', 'Beta', 'alpha'])
  })
  it('sorts numbers', () => {
    expect(sortItems([{ v: 3 }, { v: 1 }, { v: 2 }], (r) => r.v, 'asc').map((r) => r.v)).toEqual([1, 2, 3])
  })
})
