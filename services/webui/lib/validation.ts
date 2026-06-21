// Strict Israeli field guards for the add/edit forms. Each validator assumes a non-empty
// value (the form handles required/empty separately) and returns a Hebrew error or null.

const digits = (v: string) => v.replace(/\D/g, '')

/** Vehicle licensing plate: a 7–8 digit number (hyphens allowed, stripped). */
export function plate(v: string): string | null {
  const d = digits(v)
  return d.length >= 7 && d.length <= 8 ? null : 'מספר רישוי חייב להיות 7–8 ספרות'
}

/** Driver licence number: a 7–9 digit number. */
export function driverLicense(v: string): string | null {
  const d = digits(v)
  return d.length >= 7 && d.length <= 9 ? null : 'מספר רישיון נהג חייב להיות 7–9 ספרות'
}

/** Israeli mobile: 05X followed by 7 digits (10 digits total). */
export function phoneIL(v: string): string | null {
  return /^05\d{8}$/.test(digits(v)) ? null : 'מספר טלפון חייב להיות נייד ישראלי תקין'
}

export function email(v: string): string | null {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim()) ? null : 'כתובת דוא״ל לא תקינה'
}

/** Non-negative integer (km, maintenance km). */
export function nonNegInt(v: string): string | null {
  return /^\d+$/.test(v.trim()) ? null : 'חייב להיות מספר שלם אי-שלילי'
}
