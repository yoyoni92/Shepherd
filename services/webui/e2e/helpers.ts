import { expect, type Page, type Locator } from '@playwright/test'

// Seeded app users (db/seed.py `_seed_app_users`): a system admin with no company
// and a company_admin bound to the Default Company. Passwords default to `shepherd`.
export const ADMIN = { email: 'admin@shepherd.ai', password: 'shepherd' }
export const COMPANY_ADMIN = { email: 'company@shepherd.ai', password: 'shepherd' }

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

// Open a company's Drive settings dialog from the Companies tab and wait until the
// async GET /settings has hydrated the form. The dialog's effect resets the
// credentials textarea to "" when settings arrive, so interacting before hydration
// races the effect and gets silently overwritten. We block on the GET response, then
// on the "configured" status badge, which renders only once settings have loaded -
// proving the hydration effect has run. (Attendance is no longer in this dialog; it
// is a per-row switch on the Companies table - see setAttendanceFlag.)
export async function openCompanySettings(
  page: Page,
  companyName: string,
): Promise<{ dialog: Locator }> {
  const respPromise = page.waitForResponse(
    (r) => /\/companies\/[^/]+\/settings(\?|$)/.test(r.url()) && r.request().method() === 'GET',
  )
  await page.locator('tr', { hasText: companyName }).getByRole('button', { name: 'הגדרות' }).click()

  const dialog = page.getByRole('dialog')
  await expect(dialog.getByText(`הגדרות חברה · ${companyName}`)).toBeVisible()

  await respPromise
  // The Drive-credentials status badge (מוגדר ✓ / לא מוגדר) is rendered only once the
  // GET has resolved, so its presence proves the hydration effect has run.
  await expect(dialog.getByText('מוגדר').first()).toBeVisible()

  // The Companies page fires a settings GET per row (each AttendanceToggle) that shares
  // this dialog's query key; under load one can resolve late and re-run the dialog's
  // hydration effect, wiping any value a caller just typed. Wait for the network to
  // settle so the form is stable before the caller interacts with it.
  await page.waitForLoadState('networkidle')

  return { dialog }
}
