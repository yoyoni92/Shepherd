import { expect, type Page, type Locator } from '@playwright/test'

// Seeded app users (db/seed.py `_seed_app_users`): a system admin with no company
// and a company_admin bound to the Default Company. Passwords default to `shepherd`.
export const ADMIN = { email: 'admin@fleetops.io', password: 'shepherd' }
export const COMPANY_ADMIN = { email: 'company@fleetops.io', password: 'shepherd' }

// Drive the real NextAuth credentials form (POST /auth/login via the Fleet proxy)
// and wait for the post-login redirect to /dashboard.
export async function login(page: Page, who: { email: string; password: string }): Promise<void> {
  await page.goto('/')
  await page.fill('input[type="email"]', who.email)
  await page.fill('input[type="password"]', who.password)
  await page.click('button:has-text("כניסה למערכת")')
  await expect(page).toHaveURL('/dashboard')
  // Sidebar mounted = the admin shell rendered for this session.
  await expect(page.locator('aside')).toBeVisible()
}

// Drop the NextAuth session so the next `login` starts a fresh session. Feature 5's
// attendance flag rides in the session from login, so picking up a flipped flag
// requires a clean re-login (clear cookies, not just navigate).
export async function logout(page: Page): Promise<void> {
  await page.context().clearCookies()
}

// Open a company's per-tenant settings dialog from the Companies tab and wait until
// the async GET /settings has hydrated the form. The dialog's effect resets the
// credentials textarea to "" and the attendance checkbox to the persisted value
// when settings arrive, so interacting before hydration races the effect and gets
// silently overwritten. We block on the GET response, then on the checkbox
// reflecting the persisted flag, which proves the hydration effect has run.
export async function openCompanySettings(
  page: Page,
  companyName: string,
): Promise<{ dialog: Locator; attendanceEnabled: boolean }> {
  const respPromise = page.waitForResponse(
    (r) => /\/companies\/[^/]+\/settings(\?|$)/.test(r.url()) && r.request().method() === 'GET',
  )
  await page.locator('tr', { hasText: companyName }).getByRole('button', { name: 'הגדרות' }).click()

  const dialog = page.getByRole('dialog')
  await expect(dialog.getByText(`הגדרות · ${companyName}`)).toBeVisible()

  const body = await (await respPromise).json()
  const attendanceEnabled = body?.feature_flags?.attendance === true

  // Wait for the hydration effect to apply the persisted state to the form.
  await expect(dialog.locator('input[type="checkbox"]')).toBeChecked({ checked: attendanceEnabled })

  return { dialog, attendanceEnabled }
}
