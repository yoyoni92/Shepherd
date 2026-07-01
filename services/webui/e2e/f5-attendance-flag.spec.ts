import { test, expect, type Page } from '@playwright/test'
import { ADMIN, COMPANY_ADMIN, login, logout } from './helpers'

// Feature 5 (per-tenant settings): the Attendance nav item is gated behind the
// company's `attendance` feature flag for a company_admin. The flag rides in the
// session from login (lib/nav.filterNav), so picking up a change requires a fresh
// re-login. The Default Company is seeded with attendance OFF.
const ATTENDANCE_HREF = '/attendance'
const ATTENDANCE_LABEL = 'נוכחות'

// Both tests mutate the shared Default Company attendance flag, so they must not
// run concurrently. Serial mode also makes each test set its own precondition,
// so the suite is re-runnable regardless of the flag's current persisted value.
test.describe.configure({ mode: 'serial' })

// Drive the REAL per-row attendance switch (Companies tab -> Default Company row ->
// "נוכחות" toggle) as the system admin to put the Default Company's attendance flag
// into a known state, then drop the admin session. The switch lazily loads the
// company's settings and saves immediately on click via PATCH /settings.
async function setAttendanceFlag(page: Page, on: boolean): Promise<void> {
  await login(page, ADMIN)
  await page.goto('/companies')
  await expect(page.locator('body')).not.toContainText('Application error')

  const row = page.locator('tr', { hasText: 'Default Company' })
  const toggle = row.getByRole('switch', { name: 'נוכחות' })
  // The switch is disabled until the company's settings have loaded.
  await expect(toggle).toBeEnabled()

  const isOn = (await toggle.getAttribute('aria-checked')) === 'true'
  if (isOn === on) {
    await logout(page)
    return
  }

  // Assert the save committed via the PATCH response (200), the authoritative signal
  // that the merged flag was persisted, then confirm the switch reflects the new state.
  const patchResp = page.waitForResponse(
    (r) => /\/companies\/[^/]+\/settings(\?|$)/.test(r.url()) && r.request().method() === 'PATCH',
  )
  await toggle.click()
  expect((await patchResp).status()).toBe(200)
  await expect(toggle).toHaveAttribute('aria-checked', String(on))
  await logout(page)
}

test.describe('F5 attendance feature flag', () => {
  test('company_admin does not see Attendance when the flag is off', async ({ page }) => {
    await setAttendanceFlag(page, false)

    await login(page, COMPANY_ADMIN)
    const aside = page.locator('aside')
    await expect(aside.locator(`a[href="${ATTENDANCE_HREF}"]`)).toHaveCount(0)
    await expect(aside.getByRole('link', { name: ATTENDANCE_LABEL })).toHaveCount(0)
  })

  test('enabling attendance via the settings dialog reveals the nav item after re-login', async ({ page }) => {
    await setAttendanceFlag(page, true)

    // A fresh session for the company_admin picks up attendance=true from login.
    await login(page, COMPANY_ADMIN)
    const aside = page.locator('aside')
    await expect(aside.locator(`a[href="${ATTENDANCE_HREF}"]`)).toHaveCount(1)
    await expect(aside.getByRole('link', { name: ATTENDANCE_LABEL })).toBeVisible()
  })
})
