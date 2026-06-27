import { test, expect } from '@playwright/test'
import { COMPANY_ADMIN, login } from './helpers'

// A company_admin (bound to the Default Company) sees a reduced shell: the system-only
// sections are hidden in the sidebar (lib/nav allowedRoles) and hard-blocked by the
// middleware route gate (lib/routeAccess). Their own company-scoped data still loads.
test.describe('company admin', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, COMPANY_ADMIN)
  })

  test('sidebar hides the system-only sections', async ({ page }) => {
    const aside = page.locator('aside')
    for (const href of ['/companies', '/access', '/health', '/config']) {
      await expect(aside.locator(`a[href="${href}"]`)).toHaveCount(0)
    }
  })

  test('sidebar still shows the company-scoped sections', async ({ page }) => {
    const aside = page.locator('aside')
    for (const href of ['/vehicles', '/drivers', '/bot']) {
      await expect(aside.locator(`a[href="${href}"]`)).toHaveCount(1)
    }
  })

  test('middleware redirects away from a system-only route', async ({ page }) => {
    await page.goto('/companies')
    // The role gate bounces company_admin back to /dashboard before the page renders.
    await expect(page).not.toHaveURL(/\/companies(\/|$)/)
    await expect(page).toHaveURL('/dashboard')
  })

  test('their own company vehicles load without error', async ({ page }) => {
    await page.goto('/vehicles')
    await expect(page.locator('body')).not.toContainText('Application error')
    await expect(page.getByRole('tab', { name: 'רכבים' })).toBeVisible()
  })
})
