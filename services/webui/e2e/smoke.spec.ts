import { test, expect } from '@playwright/test'

// Login -> navigate every section -> no crash.
test('login and navigate all sections without error', async ({ page }) => {
  await page.goto('/')
  await page.fill('input[type="email"]', process.env.ADMIN_EMAIL ?? 'admin@fleetops.io')
  await page.fill('input[type="password"]', process.env.ADMIN_PASSWORD ?? 'shepherd')
  await page.click('button:has-text("כניסה למערכת")')
  await expect(page).toHaveURL('/dashboard')

  // Admin shell renders: the Shepherd logo + sidebar nav
  await expect(page.locator('img[alt="Shepherd"]').first()).toBeVisible()
  await expect(page.getByRole('link', { name: 'רכבים' })).toBeVisible()

  const sections = [
    'vehicles',
    'drivers',
    'customers',
    'events',
    'attendance',
    'maintenance-types',
    'config',
    'health',
    'chat',
  ]
  for (const path of sections) {
    await page.goto(`/${path}`)
    await expect(page.locator('body')).not.toContainText('Application error')
    await expect(page.locator('aside')).toBeVisible() // sidebar present = admin shell mounted
  }
})
