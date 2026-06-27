import { test, expect } from '@playwright/test'
import { ADMIN, login } from './helpers'

// Feature 4 nav consolidation, from a system admin's seat: the system-only sections
// (companies/access/health/config) are present; maintenance-types and accidents are no
// longer top-level links but live as in-page tabs under Vehicles and Events.
test.describe('system admin', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, ADMIN)
  })

  test('sidebar exposes every system-admin section by href', async ({ page }) => {
    const aside = page.locator('aside')
    for (const href of ['/companies', '/access', '/health', '/config', '/vehicles', '/drivers', '/bot']) {
      await expect(aside.locator(`a[href="${href}"]`)).toHaveCount(1)
    }
  })

  test('consolidated sections are not top-level sidebar links', async ({ page }) => {
    const aside = page.locator('aside')
    for (const href of ['/maintenance-types', '/accidents', '/chat']) {
      await expect(aside.locator(`a[href="${href}"]`)).toHaveCount(0)
    }
  })

  test('maintenance-types is a tab inside Vehicles', async ({ page }) => {
    await page.goto('/vehicles')
    await expect(page.locator('body')).not.toContainText('Application error')
    await expect(page.getByRole('tab', { name: 'רכבים' })).toBeVisible()
    await expect(page.getByRole('tab', { name: 'סוגי טיפול' })).toBeVisible()
  })

  test('accidents is a tab inside Events', async ({ page }) => {
    await page.goto('/events')
    await expect(page.locator('body')).not.toContainText('Application error')
    await expect(page.getByRole('tab', { name: 'משימות' })).toBeVisible()
    await expect(page.getByRole('tab', { name: 'תאונות' })).toBeVisible()
  })
})
