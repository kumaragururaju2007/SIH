import { test, expect } from '@playwright/test';

test.describe('AICTE Document Validation Workstation - Smoke Test', () => {
  test('should load officer queue, display banner, and open application detail', async ({ page }) => {
    // 1. Navigate to frontend root
    await page.goto('http://localhost:5173');

    // 2. Verify persistent prototype disclaimer banner
    await expect(page.locator('text=PROTOTYPE NOTICE:')).toBeVisible();
    await expect(
      page.locator('text=The risk score and image-forensics signals are probabilities and aids; the human scrutiny officer always decides.')
    ).toBeVisible();

    // 3. Verify Officer Queue heading
    await expect(page.locator('h1')).toContainText('Risk-Ranked Scrutiny Queue');

    // 4. Verify queue table headers
    await expect(page.locator('text=Prioritized Scrutiny List')).toBeVisible();

    // 5. If applications are listed in the queue, click on the first one
    const rows = page.locator('tbody tr');
    const count = await rows.count();
    if (count > 0) {
      await rows.first().click();

      // Verify Application Scrutiny Detail opens
      await expect(page.locator('text=Return to Scrutiny Queue')).toBeVisible();
      await expect(page.locator('text=Calculated Risk Factor Breakdown')).toBeVisible();
      await expect(page.locator('text=Illustrative score. Supports the officer\'s decision; does not replace it.')).toBeVisible();
    }
  });

  test('should allow role switching to Institution and view application list', async ({ page }) => {
    await page.goto('http://localhost:5173');

    // Click role switcher in navbar
    const switchBtn = page.locator('header button:has-text("mode")');
    if (await switchBtn.isVisible()) {
      await switchBtn.click();
      await expect(page.locator('text=Switch Demo Persona')).toBeVisible();

      // Click Institution role
      await page.locator('button:has-text("Institution")').click();
      await page.locator('button:has-text("Switch Persona")').click();

      // Verify Institution Portal view
      await expect(page.locator('text=Institution Portal')).toBeVisible();
    }
  });
});
