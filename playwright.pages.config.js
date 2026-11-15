import { defineConfig } from '@playwright/test';
export default defineConfig({
  outputDir: 'test-results/pages',
  testDir: './tests/pages',
  testMatch: '*.spec.js',
  workers: 1,
  timeout: 30000,
  expect: { timeout: 5000 },
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:58763/AlertMe-Government-Deadline-Assistant/',
    reducedMotion: 'reduce',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE
      ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE }
      : {},
  },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1440, height: 1000 } } },
    { name: 'tablet', use: { viewport: { width: 768, height: 1024 } } },
    { name: 'mobile', use: { viewport: { width: 390, height: 844 } } },
  ],
  webServer: {
    command: 'npm run build:pages && node scripts/serve-pages.mjs',
    url: 'http://127.0.0.1:58763/AlertMe-Government-Deadline-Assistant/',
    env: { ALERTME_API_URL: '' },
    reuseExistingServer: false,
  },
});
