const KEY = 'alertme-pages-workspace-v1';
const categories = [
  'Personal',
  'Education',
  'Finance',
  'Health',
  'Work',
  'Other',
];
export function emptyWorkspace() {
  return {
    version: 1,
    user: {
      id: 'local',
      name: 'Your workspace',
      email: '',
      phone: '',
      preferences: { email: false, sms: false },
    },
    personal: [],
    government: [],
    notifications: [],
    delivery: { email: false, sms: false },
  };
}
function text(value, field, max, required = false) {
  if (
    typeof value !== 'string' ||
    value.length > max ||
    (required && !value.trim())
  )
    throw new Error(
      `${field} must contain ${required ? '1–' : 'at most '}${max} characters.`,
    );
  return value.trim();
}
function date(value) {
  if (
    typeof value !== 'string' ||
    !/^\d{4}-\d{2}-\d{2}$/.test(value) ||
    value < '1900-01-01' ||
    value > '2199-12-31'
  )
    throw new Error('Choose a valid date between 1900 and 2199.');
  const parsed = new Date(value + 'T12:00:00Z');
  if (!Number.isFinite(+parsed) || parsed.toISOString().slice(0, 10) !== value)
    throw new Error('Choose a valid calendar date.');
  return value;
}
function deadline(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input))
    throw new Error('Invalid deadline record.');
  if (
    !['high', 'medium', 'low'].includes(input.priority) ||
    !['pending', 'in_progress', 'completed'].includes(input.status) ||
    !categories.includes(input.category)
  )
    throw new Error('Choose valid priority, category and status values.');
  if (
    !Array.isArray(input.reminder_days) ||
    input.reminder_days.length > 5 ||
    input.reminder_days.some((d) => !Number.isInteger(d) || d < 0 || d > 30)
  )
    throw new Error('Choose up to 5 reminder days between 0 and 30.');
  return {
    id: text(input.id, 'ID', 128, true),
    title: text(input.title, 'Title', 120, true),
    description: text(input.description ?? '', 'Notes', 3000),
    due_date: date(input.due_date),
    priority: input.priority,
    status: input.status,
    category: input.category,
    reminder_days: [...new Set(input.reminder_days)],
    storage: 'main',
    type: 'personal',
  };
}
export function validateWorkspace(input) {
  if (
    !input ||
    input.version !== 1 ||
    !Array.isArray(input.personal) ||
    input.personal.length > 5000
  )
    throw new Error(
      'Choose a valid AlertMe browser backup (up to 5,000 deadlines).',
    );
  const data = emptyWorkspace();
  data.personal = input.personal.map(deadline);
  if (new Set(data.personal.map((d) => d.id)).size !== data.personal.length)
    throw new Error('The backup contains duplicate deadline IDs.');
  data.user.name = text(
    input.user?.name ?? 'Your workspace',
    'Display name',
    80,
    true,
  );
  return data;
}
export function loadLocal() {
  let raw;
  try {
    raw = localStorage.getItem(KEY);
  } catch {
    throw new Error(
      'Browser storage is unavailable. Allow site storage to save your planner.',
    );
  }
  if (raw === null) return emptyWorkspace();
  try {
    return validateWorkspace(JSON.parse(raw));
  } catch {
    throw new Error(
      'Your saved planner could not be read. Download the original data before restoring a valid backup from Settings.',
    );
  }
}
function saveLocal(data) {
  const value = validateWorkspace(data);
  try {
    localStorage.setItem(KEY, JSON.stringify(value));
  } catch {
    throw new Error(
      'Your changes could not be saved. Browser storage may be full or unavailable.',
    );
  }
  return value;
}
export function localBackup() {
  try {
    return localStorage.getItem(KEY) ?? JSON.stringify(emptyWorkspace());
  } catch {
    throw new Error('Browser storage is unavailable.');
  }
}
export function restoreLocal(raw) {
  let value;
  try {
    value = JSON.parse(raw);
  } catch {
    throw new Error('Choose a valid JSON backup.');
  }
  return saveLocal(validateWorkspace(value));
}
export async function localRequest(path, { method = 'GET', value } = {}) {
  const data = loadLocal();
  if (path === '/api/workspace' && method === 'GET') return data;
  if (path === '/api/me' && method === 'PUT') {
    if (!value || typeof value.name !== 'string')
      throw new Error('Browser-local mode supports display-name changes here.');
    data.user.name = text(value.name, 'Display name', 80, true);
    return saveLocal(data).user;
  }
  if (path === '/api/personal-deadlines' && method === 'POST') {
    if (data.personal.length >= 5000)
      throw new Error(
        'Export and archive older records before adding more than 5,000 deadlines.',
      );
    const entry = deadline({ ...value, id: crypto.randomUUID() });
    data.personal.push(entry);
    saveLocal(data);
    return { id: entry.id };
  }
  const match = path.match(/^\/api\/personal-deadlines\/([^/]+)$/);
  if (match && ['PUT', 'DELETE'].includes(method)) {
    const id = decodeURIComponent(match[1]),
      index = data.personal.findIndex((d) => d.id === id);
    if (index < 0)
      throw new Error('This deadline no longer exists. Refresh your planner.');
    if (method === 'DELETE') data.personal.splice(index, 1);
    else
      data.personal[index] = deadline({
        ...data.personal[index],
        ...value,
        id,
      });
    saveLocal(data);
    return { message: 'Deadline saved.' };
  }
  throw new Error('This feature requires the connected AlertMe API.');
}
export const localStorageKey = KEY;
