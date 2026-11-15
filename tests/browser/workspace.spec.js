import { test, expect } from '@playwright/test';
import fs from 'node:fs/promises';
const iso = (offset = 0) => {
  const d = new Date();
  d.setDate(d.getDate() + offset);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};
async function signup(page) {
  const email = `browser-${Date.now()}-${Math.random().toString(36).slice(2)}@example.test`;
  await page.goto('/');
  await page.getByRole('button', { name: 'Create an account', exact: true }).click();
  await page.getByLabel('Full name', { exact: true }).fill('Sample Account');
  await page.getByLabel('Email or phone', { exact: true }).fill(email);
  await page.getByLabel('Password', { exact: true }).fill('Browser-password123');
  const result = page.waitForResponse(
    (r) => r.url().endsWith('/signup') && r.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  const data = await (await result).json();
  await expect(page.locator('#workspace')).toBeVisible();
  return { email, token: data.token };
}
async function nav(page, view) {
  await page.goto('/#' + view);
  await expect(page.locator('#crumb')).toHaveText(
    view === 'personal' ? 'My deadlines' : view[0].toUpperCase() + view.slice(1),
  );
}
async function create(page, title = 'Renew documents', due = iso(3)) {
  await page.getByRole('button', { name: 'New deadline', exact: true }).first().click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Title', { exact: true }).fill(title);
  await dialog.getByLabel('Due date', { exact: true }).fill(due);
  await dialog
    .getByLabel('Notes', { exact: true })
    .fill('Read the requirements and prepare the documents.');
  await dialog.getByRole('button', { name: 'Save deadline', exact: true }).click();
  await expect(dialog).not.toBeVisible();
}
async function noOverflow(page) {
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
  ).toBeTruthy();
}

test('web account, personal CRUD, filtering, exports and logout work', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await signup(page);
  await create(page);
  await nav(page, 'personal');
  await expect(page.getByRole('heading', { name: 'Renew documents', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Edit Renew documents', exact: true }).click();
  await page.getByRole('dialog').getByLabel('Title', { exact: true }).fill('Renew passport');
  await page.getByRole('button', { name: 'Save deadline', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Renew passport', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Complete Renew passport', exact: true }).click();
  await expect(
    page.getByRole('button', { name: 'Reopen Renew passport', exact: true }),
  ).toBeVisible();
  await page.getByRole('searchbox').fill('not present');
  await expect(page.getByRole('heading', { name: 'Nothing on this list yet.' })).toBeVisible();
  await page.getByRole('searchbox').fill('Renew');
  const csvEvent = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export CSV' }).click();
  const csv = await csvEvent;
  expect(await fs.readFile(await csv.path(), 'utf8')).toContain('Renew passport');
  const icsEvent = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Calendar file', exact: true }).click();
  const ics = await icsEvent;
  const contents = await fs.readFile(await ics.path(), 'utf8');
  expect(contents).toContain('BEGIN:VCALENDAR');
  expect(contents).toContain('SUMMARY:Renew passport');
  await noOverflow(page);
  page.once('dialog', (d) => d.accept());
  await page.getByRole('button', { name: 'Delete Renew passport', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Renew passport', exact: true })).toHaveCount(0);
  if (test.info().project.name === 'mobile')
    await page.getByRole('button', { name: 'Toggle navigation' }).click();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page.locator('#auth')).toBeVisible();
  await page.reload();
  await expect(page.locator('#auth')).toBeVisible();
  expect(errors).toEqual([]);
});

test('published deadlines follow through to the calendar', async ({ page }) => {
  await signup(page);
  await nav(page, 'government');
  const card = page.locator('.feed-card').filter({
    has: page.getByRole('heading', { name: 'Sample scholarship applications', exact: true }),
  });
  await card.getByRole('button', { name: 'Follow deadline', exact: true }).click();
  await expect(card.getByRole('button', { name: 'Following ✓', exact: true })).toBeVisible();
  await nav(page, 'calendar');
  const label = new Date(iso(7) + 'T12:00:00').toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
  await page.getByRole('button', { name: label + ', deadlines scheduled', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Sample scholarship applications', exact: true }),
  ).toBeVisible();
  await noOverflow(page);
  await nav(page, 'government');
  await card.getByRole('button', { name: 'Following ✓', exact: true }).click();
  await expect(card.getByRole('button', { name: 'Follow deadline', exact: true })).toBeVisible();
});

test('administrator can publish, edit and remove a deadline', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Email or phone', { exact: true }).fill('admin@example.test');
  await page.getByLabel('Password', { exact: true }).fill('Admin-test-password123');
  await page.getByLabel('Administrator sign-in').check();
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.locator('#workspace')).toBeVisible();
  await page.getByRole('button', { name: 'Publish deadline', exact: true }).first().click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Title', { exact: true }).fill('Temporary admin publication');
  await dialog.getByLabel('Department', { exact: true }).fill('Test department');
  await dialog.getByLabel('Source URL', { exact: true }).fill('https://example.gov/official');
  await dialog.getByRole('button', { name: 'Publish deadline', exact: true }).click();
  const card = page.locator('.feed-card').filter({
    has: page.getByRole('heading', { name: 'Temporary admin publication', exact: true }),
  });
  await expect(card).toBeVisible();
  await card.getByRole('button', { name: 'Edit deadline', exact: true }).click();
  await page
    .getByRole('dialog')
    .getByLabel('Title', { exact: true })
    .fill('Updated admin publication');
  await page
    .getByRole('dialog')
    .getByRole('button', { name: 'Publish deadline', exact: true })
    .click();
  const updated = page
    .locator('.feed-card')
    .filter({ has: page.getByRole('heading', { name: 'Updated admin publication', exact: true }) });
  page.once('dialog', (d) => d.accept());
  await updated.getByRole('button', { name: 'Delete', exact: true }).click();
  await expect(updated).toHaveCount(0);
  await noOverflow(page);
});

test('verified contacts enable preferences and password updates end the old session', async ({
  page,
}) => {
  const account = await signup(page);
  await nav(page, 'settings');
  await page.getByRole('button', { name: 'Verify email', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  const response = await page.request.get(
    '/_test/email-code?email=' + encodeURIComponent(account.email),
  );
  const code = (await response.json()).code;
  await page.getByLabel('6-digit code', { exact: true }).fill(code);
  await page
    .getByRole('dialog')
    .getByRole('button', { name: 'Verify contact', exact: true })
    .click();
  await expect(page.locator('.contact-row').first()).toContainText('Verified');
  await page.getByLabel('Email reminders', { exact: true }).check();
  await page.getByRole('button', { name: 'Save reminder preferences', exact: true }).click();
  await expect(page.getByLabel('Email reminders', { exact: true })).toBeChecked();
  await page.getByLabel('Current password', { exact: true }).fill('Browser-password123');
  await page.getByLabel('New password', { exact: true }).fill('Changed-password123');
  await page.getByRole('button', { name: 'Update password', exact: true }).click();
  await expect(page.locator('#auth')).toBeVisible();
  await page.getByLabel('Email or phone', { exact: true }).fill(account.email);
  await page.getByLabel('Password', { exact: true }).fill('Changed-password123');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.locator('#workspace')).toBeVisible();
});

test('a failed save keeps the draft until a successful retry', async ({ page }) => {
  await signup(page);
  await page.getByRole('button', { name: 'New deadline', exact: true }).first().click();
  await page.getByRole('dialog').getByLabel('Title', { exact: true }).fill('Retain this draft');
  await page.route('**/api/personal-deadlines', async (route) => {
    if (route.request().method() === 'POST')
      await route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Database unavailable. Please try again.' }),
      });
    else await route.continue();
  });
  await page
    .getByRole('dialog')
    .getByRole('button', { name: 'Save deadline', exact: true })
    .click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.locator('#editor-error')).toContainText('Database unavailable');
  await expect(page.getByRole('dialog').getByLabel('Title', { exact: true })).toHaveValue(
    'Retain this draft',
  );
  await page.unroute('**/api/personal-deadlines');
  await page
    .getByRole('dialog')
    .getByRole('button', { name: 'Save deadline', exact: true })
    .click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await nav(page, 'personal');
  await expect(page.getByRole('heading', { name: 'Retain this draft', exact: true })).toBeVisible();
});

test('workspace layouts, keyboard dialogs and accessibility stay usable', async ({ page }) => {
  const { default: AxeBuilder } = await import('@axe-core/playwright');
  await page.goto('/');
  await noOverflow(page);
  await page.screenshot({ path: test.info().outputPath('sign-in.png'), fullPage: true });
  const account = await signup(page);
  const names = [
    'Renew identity documents',
    'Submit scholarship application',
    'Review insurance renewal',
    'Prepare tax documents',
    'Medical appointment',
    'Course registration',
    'Update address details',
  ];
  for (let i = 0; i < names.length; i++) {
    const response = await page.request.post('/api/personal-deadlines', {
      headers: { Authorization: 'Bearer ' + account.token },
      data: {
        title: names[i],
        description: 'Synthetic fixture for interface verification.',
        due_date: iso(i - 1),
        priority: ['high', 'medium', 'low'][i % 3],
        category: ['Personal', 'Education', 'Finance'][i % 3],
      },
    });
    expect(response.status()).toBe(201);
  }
  await page.getByRole('button', { name: 'Refresh deadlines', exact: true }).click();
  await expect(
    page.locator('.deadline-row').filter({
      has: page.getByRole('heading', { name: 'Submit scholarship application', exact: true }),
    }),
  ).toBeVisible();
  await noOverflow(page);
  await page.screenshot({ path: test.info().outputPath('overview.png'), fullPage: true });
  for (const target of [
    'overview',
    'personal',
    'government',
    'calendar',
    'reminders',
    'settings',
  ]) {
    await nav(page, target);
    await noOverflow(page);
    const scan = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    expect(scan.violations.map((v) => ({ id: v.id, nodes: v.nodes.map((n) => n.target) }))).toEqual(
      [],
    );
  }
  await nav(page, 'calendar');
  await page.screenshot({ path: test.info().outputPath('calendar.png'), fullPage: true });
  await nav(page, 'personal');
  await page.getByRole('button', { name: 'New deadline', exact: true }).first().click();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  if (test.info().project.name === 'mobile') {
    await page.getByRole('button', { name: 'Toggle navigation' }).click();
    await page.getByRole('link', { name: 'Government', exact: true }).click();
    await expect(page.locator('#sidebar')).not.toHaveClass(/open/);
  }
});

test('saving settings preserves drafts in other forms', async ({ page }) => {
  const account = await signup(page);
  await nav(page, 'settings');
  await page.getByRole('button', { name: 'Verify email', exact: true }).click();
  const code = (
    await (
      await page.request.get('/_test/email-code?email=' + encodeURIComponent(account.email))
    ).json()
  ).code;
  await page.getByLabel('6-digit code', { exact: true }).fill(code);
  await page
    .getByRole('dialog')
    .getByRole('button', { name: 'Verify contact', exact: true })
    .click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  let received, release;
  const started = new Promise((resolve) => (received = resolve));
  const gate = new Promise((resolve) => (release = resolve));
  await page.route('**/api/me', async (route) => {
    if (route.request().method() === 'PUT' && route.request().postDataJSON()?.preferences) {
      received();
      await gate;
    }
    await route.continue();
  });
  await page.getByLabel('Email reminders', { exact: true }).check();
  await page.getByRole('button', { name: 'Save reminder preferences', exact: true }).click();
  await started;
  await page.getByLabel('Current password', { exact: true }).fill('Browser-password123');
  await page.getByLabel('New password', { exact: true }).fill('Retained-password123');
  release();
  await expect(page.getByRole('status')).toHaveText('Reminder preferences saved.');
  await expect(page.getByLabel('Current password', { exact: true })).toHaveValue(
    'Browser-password123',
  );
  await expect(page.getByLabel('New password', { exact: true })).toHaveValue(
    'Retained-password123',
  );
  await page.getByRole('button', { name: 'Update password', exact: true }).click();
  await expect(page.locator('#auth')).toBeVisible();
});
