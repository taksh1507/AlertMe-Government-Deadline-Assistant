import { defineConfig } from '@playwright/test';
export default defineConfig({
  outputDir: 'test-results/connected',
  testDir: './tests/browser',
  testMatch: '*.spec.js',
  workers: 1,
  fullyParallel: false,
  timeout: 45000,
  expect: { timeout: 7000 },
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:58762',
    reducedMotion: 'reduce',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
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
    command: `${process.env.ALERTME_TEST_PYTHON || 'python'} tests/browser/server.py`,
    url: 'http://127.0.0.1:58762/health',
    reuseExistingServer: false,
    timeout: 30000,
  },
});
