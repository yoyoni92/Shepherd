import { test, expect } from '@playwright/test'

// T8: login -> navigate every section -> no crash.
test('login and navigate all sections without error', async ({ page }) => {
  await page.goto('/')
  await page.fill('input[type="email"]', process.env.ADMIN_EMAIL ?? 'admin@fleet.co.il')
  await page.fill('input[type="password"]', process.env.ADMIN_PASSWORD ?? 'shepherd-admin')
  await page.click('button:has-text("כניסה למערכת")')
  await expect(page).toHaveURL('/dashboard')

  // Sidebar shell renders on every section
  await expect(page.locator('text=ניהול צי רכב')).toBeVisible()

  for (const path of ['vehicles', 'drivers', 'missions', 'attendance', 'config', 'chat']) {
    await page.goto(`/${path}`)
    await expect(page.locator('body')).not.toContainText('Application error')
  }
})
