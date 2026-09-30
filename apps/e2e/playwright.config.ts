import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 120_000,
  retries: 1,
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3030',
    headless: true,
    screenshot: 'only-on-failure',
  },
  webServer: undefined, // Expects docker compose to be running
});
