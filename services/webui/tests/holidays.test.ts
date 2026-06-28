import { describe, it, expect } from 'vitest'
import { monthHolidays, holidayMap } from '@/lib/holidays'

// Pesach 2026 (Israeli schedule): Erev Pesach Apr 1, Pesach I Apr 2 & Pesach VII Apr 8 are
// חג (no work); Chol HaMoed (Apr 3-7) is a מועד where work is permitted.
describe('monthHolidays (Pesach 2026, il schedule)', () => {
  const hs = monthHolidays('2026-04')
  const byDay = (d: number) => hs.find((h) => h.day === d)

  it('marks Erev Pesach as ערב חג', () => {
    expect(byDay(1)?.kind).toBe('erev')
  })

  it('marks Pesach day 1 and day 7 as חג', () => {
    expect(byDay(2)?.kind).toBe('chag')
    expect(byDay(8)?.kind).toBe('chag')
  })

  it('marks Chol HaMoed as a minor מועד (still a work day)', () => {
    expect(byDay(5)?.kind).toBe('minor')
  })

  it('returns named, date-labelled, day-sorted entries', () => {
    expect(byDay(2)?.name?.length).toBeGreaterThan(0)
    expect(byDay(2)?.dateLabel).toBe('02/04')
    expect(hs.map((h) => h.day)).toEqual([...hs.map((h) => h.day)].sort((a, b) => a - b))
  })

  it('holidayMap keys entries by day-of-month', () => {
    expect(holidayMap('2026-04').get(8)?.kind).toBe('chag')
  })
})
