import { test, expect } from '@playwright/test'

// T8: login -> navigate each screen -> no crash; one happy-path upload
test('login and navigate all screens without error', async ({ page }) => {
  await page.goto('/')
  await page.fill('input[type="email"]', process.env.ADMIN_EMAIL ?? 'admin@fleetops.io')
  await page.fill('input[type="password"]', process.env.ADMIN_PASSWORD ?? 'shepherd-admin')
  await page.click('button:has-text("Sign in")')
  await expect(page).toHaveURL('/dashboard')

  for (const path of ['chat', 'assistant', 'upload', 'config', 'review']) {
    await page.goto(`/${path}`)
    await expect(page.locator('h2')).toBeVisible()
    await expect(page.locator('body')).not.toContainText('Application error')
  }
})
