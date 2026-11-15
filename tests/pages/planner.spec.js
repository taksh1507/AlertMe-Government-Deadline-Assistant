import { test, expect } from '@playwright/test';
import fs from 'node:fs/promises';
const base = '/AlertMe-Government-Deadline-Assistant/';
const key = 'alertme-pages-workspace-v1';
const today = () => new Date().toLocaleDateString('en-CA');
async function nav(page, view) {
  await page.goto(base + '#' + view);
  await expect(page.locator('#crumb')).toHaveText(
    view === 'personal'
      ? 'My deadlines'
      : view[0].toUpperCase() + view.slice(1),
  );
}
async function add(page, title = 'Local deadline') {
  await page
    .getByRole('button', { name: 'New deadline', exact: true })
    .first()
    .click();
  await page
    .getByRole('dialog')
    .getByLabel('Title', { exact: true })
    .fill(title);
  await page
    .getByRole('dialog')
    .getByLabel('Due date', { exact: true })
    .fill(today());
  await page
    .getByRole('dialog')
    .getByRole('button', { name: 'Save deadline', exact: true })
    .click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
}
test('published subdirectory works without API requests and preserves local deadlines', async ({
  page,
}) => {
  const errors = [],
    apiRequests = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('request', (r) => {
    if (new URL(r.url()).pathname.startsWith('/api/'))
      apiRequests.push(r.url());
  });
  await page.goto(base);
  await expect(page.locator('#workspace')).toBeVisible();
  await expect(page.locator('#local-mode-note')).toBeVisible();
  await expect(page.locator('#auth')).not.toBeVisible();
  await add(page);
  await page
    .getByRole('button', { name: 'Edit Local deadline', exact: true })
    .click();
  await page
    .getByRole('dialog')
    .getByLabel('Title', { exact: true })
    .fill('Updated local deadline');
  await page
    .getByRole('button', { name: 'Save deadline', exact: true })
    .click();
  await page
    .getByRole('button', {
      name: 'Complete Updated local deadline',
      exact: true,
    })
    .click();
  await expect(
    page.getByRole('button', {
      name: 'Reopen Updated local deadline',
      exact: true,
    }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole('button', {
      name: 'Reopen Updated local deadline',
      exact: true,
    }),
  ).toBeVisible();
  const csvEvent = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export CSV' }).click();
  const csv = await csvEvent;
  expect(await fs.readFile(await csv.path(), 'utf8')).toContain(
    'Updated local deadline',
  );
  await nav(page, 'calendar');
  await expect(page.locator('.calendar-large')).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  expect(apiRequests).toEqual([]);
  expect(errors).toEqual([]);
});
test('local backup restore and local-only settings are usable', async ({
  page,
}) => {
  await page.goto(base);
  await add(page, 'Keep this');
  await nav(page, 'settings');
  await page.getByLabel('Display name').fill('My browser');
  await page.getByRole('button', { name: 'Save name', exact: true }).click();
  await expect(page.locator('#account-name')).toHaveText('My browser');
  await expect(
    page.getByLabel('Current password', { exact: true }),
  ).toHaveCount(0);
  const downloadEvent = page.waitForEvent('download');
  await page
    .getByRole('button', { name: 'Download backup', exact: true })
    .click();
  const backup = await downloadEvent;
  await nav(page, 'personal');
  await add(page, 'Temporary');
  await page.locator('#local-import').setInputFiles(await backup.path());
  await page.getByLabel('Confirmation', { exact: true }).fill('RESTORE');
  await page
    .getByRole('button', { name: 'Restore backup', exact: true })
    .last()
    .click();
  await nav(page, 'personal');
  await expect(
    page.getByRole('heading', { name: 'Keep this', exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Temporary', exact: true }),
  ).toHaveCount(0);
  await page.locator('#local-import').setInputFiles({
    name: 'bad.json',
    mimeType: 'application/json',
    buffer: Buffer.from('{}'),
  });
  await expect(page.locator('#error-banner')).toContainText('not a valid');
  await expect(
    page.getByRole('heading', { name: 'Keep this', exact: true }),
  ).toBeVisible();
});
test('corrupt local data stays recoverable and input remains plain text', async ({
  page,
}) => {
  await page.addInitScript((k) => localStorage.setItem(k, '{broken'), key);
  await page.goto(base);
  await expect(page.locator('#error-banner')).toContainText(
    'could not be read',
  );
  await expect(
    page.getByRole('button', { name: 'New deadline', exact: true }),
  ).toBeDisabled();
  expect(await page.evaluate((k) => localStorage.getItem(k), key)).toBe(
    '{broken',
  );
  await nav(page, 'settings');
  const event = page.waitForEvent('download');
  await page
    .getByRole('button', { name: 'Download backup', exact: true })
    .click();
  expect(await fs.readFile(await (await event).path(), 'utf8')).toBe('{broken');
});
test('Pages edition keeps useful landmarks and contrast', async ({ page }) => {
  const { default: AxeBuilder } = await import('@axe-core/playwright');
  await page.goto(base);
  await add(page, 'A date worth remembering');
  for (const view of [
    'overview',
    'personal',
    'calendar',
    'reminders',
    'settings',
  ]) {
    await nav(page, view);
    const result = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    expect(
      result.violations.map((v) => ({
        id: v.id,
        nodes: v.nodes.map((n) => n.target),
      })),
    ).toEqual([]);
  }
  if (test.info().project.name === 'mobile') {
    await page.getByRole('button', { name: 'Toggle navigation' }).click();
    await page.getByRole('link', { name: 'My deadlines', exact: true }).click();
    await expect(page.locator('#sidebar')).not.toHaveClass(/open/);
  }
});
