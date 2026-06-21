import { describe, it, expect } from 'vitest'
import { plate, driverLicense, phoneIL, email, nonNegInt } from '@/lib/validation'

describe('validation guards', () => {
  it('plate accepts 7–8 digits (hyphens ignored), rejects others', () => {
    expect(plate('12-345-67')).toBeNull()
    expect(plate('1234567')).toBeNull()
    expect(plate('12345678')).toBeNull()
    expect(plate('123456')).not.toBeNull()
    expect(plate('123456789')).not.toBeNull()
  })

  it('driverLicense accepts 7–9 digits', () => {
    expect(driverLicense('1234567')).toBeNull()
    expect(driverLicense('123456789')).toBeNull()
    expect(driverLicense('123456')).not.toBeNull()
  })

  it('phoneIL requires an Israeli mobile', () => {
    expect(phoneIL('050-123-4567')).toBeNull()
    expect(phoneIL('0501234567')).toBeNull()
    expect(phoneIL('03-1234567')).not.toBeNull()
    expect(phoneIL('123')).not.toBeNull()
  })

  it('email validates format', () => {
    expect(email('a@b.co.il')).toBeNull()
    expect(email('nope')).not.toBeNull()
  })

  it('nonNegInt rejects negatives and non-integers', () => {
    expect(nonNegInt('0')).toBeNull()
    expect(nonNegInt('1500')).toBeNull()
    expect(nonNegInt('-5')).not.toBeNull()
    expect(nonNegInt('1.5')).not.toBeNull()
  })
})
