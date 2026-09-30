import { test, expect } from '@playwright/test';

test.describe('Ogma Manga Reader E2E', () => {
  test('should load the homepage and show the input form', async ({ page }) => {
    await page.goto('/');
    
    // Check if the main heading is present
    await expect(page.locator('text=Ogma')).toBeVisible();
    
    // Check if the input field is present
    const input = page.locator('input[placeholder="Paste MangaDex Chapter URL here..."]');
    await expect(input).toBeVisible();
    
    // Check if the translate button is present
    const button = page.locator('button:has-text("Translate")');
    await expect(button).toBeVisible();
  });
});
