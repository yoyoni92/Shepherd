import { test, expect } from '@playwright/test'
import { ADMIN, login, openCompanySettings } from './helpers'

// Feature 5 (per-tenant settings): the per-company Drive credentials are validated
// server-side on PATCH /companies/{id}/settings (validate-then-persist). Pasting
// non-JSON fails the JSON parse before any Google network call, and the backend
// returns 400 with the exact detail "Credentials are not valid JSON.", which the
// dialog surfaces inline. The credentials blob is write-only: reads never return it,
// so the textarea always starts empty (a "מוגדר ✓" badge is the only configured hint).
test.describe('F5 Drive credential validation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, ADMIN)
    await page.goto('/companies')
    await expect(page.locator('body')).not.toContainText('Application error')
  })

  test('invalid (non-JSON) credentials surface the backend validation error inline', async ({ page }) => {
    const { dialog } = await openCompanySettings(page, 'Default Company')

    // Write-only secret: the textarea must not echo any stored credentials.
    const creds = dialog.locator('textarea')
    await expect(creds).toHaveValue('')

    await dialog.locator('input:not([type="checkbox"])').first().fill('some-folder-id')
    await creds.fill('not-json')
    await dialog.getByRole('button', { name: 'שמירה' }).click()

    // The server's 400 detail is propagated through the proxy to the dialog.
    await expect(dialog.getByText('Credentials are not valid JSON.')).toBeVisible({ timeout: 15000 })
    // Nothing was stored, so no success confirmation appears.
    await expect(dialog.getByText('ההגדרות נשמרו ✓')).toHaveCount(0)
  })

  test('the credentials textarea is write-only (never displays a stored secret)', async ({ page }) => {
    const { dialog } = await openCompanySettings(page, 'Default Company')
    // Always empty on open regardless of what is persisted server-side.
    await expect(dialog.locator('textarea')).toHaveValue('')
  })
})
