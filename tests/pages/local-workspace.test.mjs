import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import {
  emptyWorkspace,
  localRequest,
  localBackup,
  restoreLocal,
  validateWorkspace,
  loadLocal,
  localStorageKey,
} from '../../Alertme/src/web/static/local-workspace.js';
const saved = new Map();
globalThis.localStorage = {
  getItem: (k) => saved.get(k) ?? null,
  setItem: (k, v) => saved.set(k, v),
};
beforeEach(() => saved.clear());
const entry = {
  title: 'Renew documents',
  description: 'Check requirements',
  due_date: '2026-12-01',
  priority: 'high',
  status: 'pending',
  category: 'Personal',
  reminder_days: [3, 1, 0],
};
test('local CRUD preserves identifiers and persists across reads', async () => {
  const { id } = await localRequest('/api/personal-deadlines', {
    method: 'POST',
    value: entry,
  });
  await localRequest('/api/personal-deadlines/' + id, {
    method: 'PUT',
    value: { title: 'Changed', id: 'replacement' },
  });
  assert.equal(loadLocal().personal[0].id, id);
  assert.equal(loadLocal().personal[0].title, 'Changed');
  await localRequest('/api/personal-deadlines/' + id, { method: 'DELETE' });
  assert.equal(loadLocal().personal.length, 0);
});
test('invalid dates and typed values cannot replace saved data', async () => {
  await localRequest('/api/personal-deadlines', {
    method: 'POST',
    value: entry,
  });
  const original = localBackup();
  for (const value of [
    { due_date: '2026-02-30' },
    { priority: 'urgent' },
    { reminder_days: [true] },
    { title: { bad: true } },
  ])
    await assert.rejects(
      localRequest('/api/personal-deadlines', {
        method: 'POST',
        value: { ...entry, ...value },
      }),
    );
  assert.equal(localBackup(), original);
});
test('backup restore validates records and preserves names', async () => {
  await localRequest('/api/me', { method: 'PUT', value: { name: 'Taksh' } });
  await localRequest('/api/personal-deadlines', {
    method: 'POST',
    value: entry,
  });
  const backup = localBackup();
  saved.clear();
  restoreLocal(backup);
  assert.equal(loadLocal().user.name, 'Taksh');
  assert.equal(loadLocal().personal.length, 1);
});
test('invalid or duplicate-ID backups leave existing records intact', async () => {
  await localRequest('/api/personal-deadlines', {
    method: 'POST',
    value: entry,
  });
  const original = localBackup(),
    data = loadLocal();
  assert.throws(() => restoreLocal('bad json'));
  assert.throws(() =>
    validateWorkspace({
      ...data,
      personal: [data.personal[0], data.personal[0]],
    }),
  );
  assert.equal(localBackup(), original);
});
test('unreadable data is retained for manual recovery', async () => {
  saved.set(localStorageKey, '{broken');
  assert.throws(loadLocal, /could not be read/);
  await assert.rejects(
    localRequest('/api/personal-deadlines', { method: 'POST', value: entry }),
  );
  assert.equal(localBackup(), '{broken');
  restoreLocal(JSON.stringify(emptyWorkspace()));
  assert.equal(loadLocal().personal.length, 0);
});
test('failed storage writes are explicit and do not report persistence', async () => {
  const set = localStorage.setItem;
  localStorage.setItem = () => {
    throw new Error('QuotaExceeded');
  };
  try {
    await assert.rejects(
      localRequest('/api/personal-deadlines', { method: 'POST', value: entry }),
      /could not be saved/,
    );
  } finally {
    localStorage.setItem = set;
  }
  assert.equal(loadLocal().personal.length, 0);
});
