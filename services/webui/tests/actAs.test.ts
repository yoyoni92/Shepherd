import { describe, it, expect, beforeEach } from 'vitest'
import {
  parseActAs,
  setActAsCookies,
  clearActAsCookies,
  ACT_AS_COMPANY_COOKIE,
  ACT_AS_STATE_COOKIE,
} from '@/lib/actAs'

function readCookie(name: string): string {
  const m = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'))
  return m ? decodeURIComponent(m[1]) : ''
}

describe('parseActAs', () => {
  it('returns null for missing/empty input', () => {
    expect(parseActAs(undefined)).toBeNull()
    expect(parseActAs(null)).toBeNull()
    expect(parseActAs('')).toBeNull()
  })

  it('returns null for malformed JSON', () => {
    expect(parseActAs('{not json')).toBeNull()
  })

  it('returns null when company_id is missing', () => {
    expect(parseActAs(JSON.stringify({ name: 'X' }))).toBeNull()
  })

  it('parses a full state blob', () => {
    const raw = JSON.stringify({ company_id: 'co1', name: 'Acme', feature_flags: { attendance: true } })
    expect(parseActAs(raw)).toEqual({ company_id: 'co1', name: 'Acme', feature_flags: { attendance: true } })
  })

  it('defaults name + flags when only company_id is present', () => {
    expect(parseActAs(JSON.stringify({ company_id: 'co2' }))).toEqual({
      company_id: 'co2',
      name: '',
      feature_flags: {},
    })
  })
})

describe('setActAsCookies / clearActAsCookies', () => {
  beforeEach(() => {
    // Wipe any cookies a prior test left behind.
    for (const c of document.cookie.split(';')) {
      const k = c.split('=')[0].trim()
      if (k) document.cookie = `${k}=; path=/; max-age=0`
    }
  })

  it('writes both cookies and round-trips through parseActAs', () => {
    const state = { company_id: 'co7', name: 'נמלי', feature_flags: { attendance: true } }
    setActAsCookies(state)
    expect(readCookie(ACT_AS_COMPANY_COOKIE)).toBe('co7')
    expect(parseActAs(readCookie(ACT_AS_STATE_COOKIE))).toEqual(state)
  })

  it('clears both cookies', () => {
    setActAsCookies({ company_id: 'co7', name: 'X', feature_flags: {} })
    clearActAsCookies()
    expect(readCookie(ACT_AS_COMPANY_COOKIE)).toBe('')
    expect(readCookie(ACT_AS_STATE_COOKIE)).toBe('')
  })
})
