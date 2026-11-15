import { icon } from './icons.js';
const $ = (id) => document.getElementById(id);
const esc = (value) =>
  String(value ?? '').replace(
    /[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c],
  );
const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};
const dayNumber = (value) => Math.floor(new Date(value + 'T12:00:00Z').getTime() / 86400000);
const displayDate = (value) =>
  /^\d{4}-\d{2}-\d{2}$/.test(value || '')
    ? new Date(value + 'T12:00:00').toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      })
    : 'Date unavailable';
const daysLeft = (item) => dayNumber(item.due_date) - dayNumber(today());
const statusText = (item) =>
  !Number.isFinite(daysLeft(item))
    ? 'Date unavailable'
    : item.status === 'completed'
      ? 'Completed'
      : daysLeft(item) < 0
        ? `${Math.abs(daysLeft(item))} ${Math.abs(daysLeft(item)) === 1 ? 'day' : 'days'} overdue`
        : daysLeft(item) === 0
          ? 'Due today'
          : `In ${daysLeft(item)} ${daysLeft(item) === 1 ? 'day' : 'days'}`;
const pathFor = (item) =>
  (item.storage === 'legacy' ? '/api/deadlines/' : '/api/personal-deadlines/') +
  encodeURIComponent(item.id);
const titleCase = (value) =>
  String(value || '')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
const config = {
  overview: ['One less thing to keep in mind.', 'Your important dates, all in one place.'],
  personal: ['Make room for your plans.', 'Add, organize and complete your personal deadlines.'],
  government: [
    'Important dates. Clear next steps.',
    'Published by your administrator. Check the source for official details.',
  ],
  calendar: ['See the bigger picture.', 'Your personal dates and subscribed deadlines, together.'],
  reminders: ['A timely little nudge.', 'Delivery history from the configured reminder worker.'],
  settings: ['Make yourself at home.', 'Your account and reminder preferences.'],
};
let data = null,
  view = 'overview',
  signup = false,
  query = '',
  priority = 'all',
  status = 'all',
  page = 1,
  calendarMonth = today().slice(0, 7),
  selectedDate = today(),
  editorSubmit = null,
  loadSerial = 0,
  toastTimer;
document.querySelectorAll('[data-icon]').forEach((n) => (n.innerHTML = icon(n.dataset.icon)));
async function api(path, { method = 'GET', value } = {}) {
  const headers = { Accept: 'application/json' };
  if (value !== undefined) headers['Content-Type'] = 'application/json';
  const csrf = document.cookie
    .split('; ')
    .find((v) => v.startsWith('csrf_access_token='))
    ?.split('=')[1];
  if (csrf) headers['X-CSRF-TOKEN'] = decodeURIComponent(csrf);
  let response;
  try {
    response = await fetch(path, {
      method,
      headers,
      credentials: 'same-origin',
      body: value === undefined ? undefined : JSON.stringify(value),
    });
  } catch {
    throw new Error('Could not reach AlertMe. Check your connection and try again.');
  }
  let result;
  try {
    result = await response.json();
  } catch {
    throw new Error('The server returned an unreadable response. Please try again.');
  }
  if (!response.ok) {
    if (response.status === 401 && data) showAuth('Your session ended. Sign in again to continue.');
    throw new Error(result.message || 'The request could not be completed.');
  }
  return result;
}
function toast(message) {
  $('toast').textContent = message;
  $('toast').hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ($('toast').hidden = true), 4500);
}
function showError(message) {
  $('error-banner').textContent = message;
  $('error-banner').hidden = false;
}
function showAuth(message = '') {
  loadSerial++;
  if (signup) $('auth-switch').click();
  $('auth-admin').checked = false;
  $('auth-identifier').value = '';
  $('auth-name').value = '';
  $('auth-phone').value = '';
  data = null;
  $('workspace').hidden = true;
  $('auth').hidden = false;
  $('view').replaceChildren();
  $('auth-password').value = '';
  $('auth-error').textContent = message;
  $('editor').close();
  $('editor-fields').replaceChildren();
  $('sidebar').classList.remove('open');
}
async function loadWorkspace() {
  const serial = ++loadSerial;
  $('refresh').disabled = true;
  try {
    const result = await api('/api/workspace');
    if (serial !== loadSerial) return;
    data = result;
    $('auth').hidden = true;
    $('workspace').hidden = false;
    $('error-banner').hidden = true;
    $('sync-label').textContent = 'Up to date';
    if (data.user.is_admin && ['overview', 'personal', 'reminders'].includes(view))
      view = 'government';
    render();
  } catch (error) {
    if (serial !== loadSerial) return;
    if (data) {
      showError(error.message + ' Your current view is retained. Use Refresh to retry.');
      $('sync-label').textContent = 'Refresh needed';
    } else showAuth(error.message === 'Sign in to continue.' ? '' : error.message);
  } finally {
    $('refresh').disabled = false;
  }
}
function userEntries() {
  return [
    ...(data?.personal || []),
    ...(data?.government || []).filter((d) => d.subscribed || data?.user?.is_admin),
  ];
}
function viewEntries() {
  return view === 'government'
    ? data.government
    : view === 'personal'
      ? data.personal
      : userEntries();
}
function filtered() {
  return viewEntries()
    .filter(
      (d) =>
        `${d.title} ${d.description || ''} ${d.department || ''}`
          .toLowerCase()
          .includes(query.toLowerCase()) &&
        (priority === 'all' || d.priority === priority) &&
        (status === 'all' || status === 'overdue'
          ? status !== 'overdue' || (daysLeft(d) < 0 && d.status !== 'completed')
          : d.status === status),
    )
    .sort((a, b) => String(a.due_date).localeCompare(String(b.due_date)));
}
function empty(title, description, action = '', kind = 'new') {
  return `<div class="empty"><span class="icon">${icon('calendar')}</span><h3>${esc(title)}</h3><p>${esc(description)}</p>${action ? `<button class="button primary" data-action="${kind}">${esc(action)}</button>` : ''}</div>`;
}
function panelHeader(title, subtitle = '', link = '', target = '') {
  return `<div class="panel-header"><div><h2>${title}</h2>${subtitle ? `<p>${subtitle}</p>` : ''}</div>${link ? `<a class="button quiet" href="#${target}">${link} ${icon('arrow')}</a>` : ''}</div>`;
}
function priorityBadge(item) {
  const value = ['high', 'medium', 'low'].includes(item.priority) ? item.priority : 'medium';
  return `<span class="badge ${value}">${titleCase(value)}</span>`;
}
function deadlineRow(item) {
  const government = item.storage === 'government',
    completed = item.status === 'completed';
  return `<article class="deadline-row">${government ? `<span class="icon">${icon('building')}</span>` : `<button class="deadline-check" data-action="complete" data-storage="${esc(item.storage)}" data-id="${esc(item.id)}" aria-label="${completed ? 'Reopen' : 'Complete'} ${esc(item.title)}" aria-pressed="${completed}">${completed ? icon('check') : ''}</button>`}<div class="deadline-copy"><h3 class="${completed ? 'done' : ''}">${esc(item.title)}</h3>${view === 'personal' && item.description ? `<p>${esc(item.description)}</p>` : ''}<div class="meta">${priorityBadge(item)}<span>${esc(item.department || item.category || 'Personal')}</span><span aria-hidden="true">·</span><span>${displayDate(item.due_date)}</span>${government ? '<span class="badge government">Following</span>' : ''}</div></div><div class="deadline-side"><strong>${statusText(item)}</strong>${completed ? '<span class="badge completed">Done</span>' : ''}</div><div class="row-actions">${government ? '' : `<button class="icon-button" data-action="edit" data-storage="${esc(item.storage)}" data-id="${esc(item.id)}" aria-label="Edit ${esc(item.title)}">${icon('edit')}</button><button class="icon-button" data-action="delete" data-storage="${esc(item.storage)}" data-id="${esc(item.id)}" aria-label="Delete ${esc(item.title)}">${icon('trash')}</button>`}</div></article>`;
}
function statistics() {
  const rows = userEntries(),
    active = rows.filter((d) => d.status !== 'completed');
  const stats = [
    [
      'Upcoming',
      active.filter((d) => daysLeft(d) >= 0).length,
      'A little room to plan',
      'calendar',
    ],
    [
      'Due this week',
      active.filter((d) => daysLeft(d) >= 0 && daysLeft(d) <= 7).length,
      'Your next seven days',
      'clock',
    ],
    ['Overdue', active.filter((d) => daysLeft(d) < 0).length, 'Worth a little attention', 'flag'],
    [
      'Completed',
      rows.filter((d) => d.status === 'completed').length,
      'One step at a time',
      'check',
    ],
  ];
  return `<div class="stats">${stats.map(([label, value, note, symbol]) => `<article class="stat"><div class="stat-top"><span>${label}</span><span class="icon">${icon(symbol)}</span></div><div class="stat-value">${value}</div><div class="stat-foot">${note}</div></article>`).join('')}</div>`;
}
function dateTile(item) {
  const d = new Date(item.due_date + 'T12:00:00');
  return `<div class="date-tile"><small>${Number.isFinite(+d) ? d.toLocaleDateString('en-IN', { month: 'short' }) : '—'}</small><strong>${Number.isFinite(+d) ? d.getDate() : '—'}</strong></div>`;
}
function calendarWidget(large = false) {
  const [year, month] = calendarMonth.split('-').map(Number),
    first = new Date(year, month - 1, 1),
    count = new Date(year, month, 0).getDate(),
    offset = (first.getDay() + 6) % 7,
    dates = new Set(userEntries().map((d) => d.due_date));
  return `<section class="panel ${large ? 'calendar-large' : ''}"><div class="mini-month-header"><button class="icon-button" data-action="prev-month" aria-label="Previous calendar month">←</button><span>${first.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })}</span><button class="icon-button" data-action="next-month" aria-label="Next calendar month">→</button></div><div class="weekdays">${['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((d) => `<span aria-hidden="true">${d}</span>`).join('')}</div><div class="month-days">${'<span></span>'.repeat(offset)}${Array.from(
    { length: count },
    (_, i) => {
      const value = `${calendarMonth}-${String(i + 1).padStart(2, '0')}`;
      return `<button class="${value === today() ? 'today' : ''} ${dates.has(value) ? 'has-date' : ''} ${large && value === selectedDate ? 'selected' : ''}" data-action="select-date" data-id="${value}" aria-label="${displayDate(value)}${dates.has(value) ? ', deadlines scheduled' : ''}">${i + 1}</button>`;
    },
  ).join(
    '',
  )}</div>${!large ? '<p class="small muted calendar-note">A dot marks a date on your list.</p>' : ''}</section>`;
}
function overview() {
  const all = userEntries(),
    pending = all
      .filter((d) => d.status !== 'completed')
      .sort((a, b) => a.due_date.localeCompare(b.due_date)),
    soon = pending.filter((d) => daysLeft(d) >= 0).slice(0, 3),
    completed = data.personal.filter((d) => d.status === 'completed').length;
  return `${statistics()}<div class="dashboard-grid"><section class="panel">${panelHeader('A little focus for today', 'The important things, without the overwhelm.', 'View all', 'personal')}${pending.length ? `<div class="list">${pending.slice(0, 5).map(deadlineRow).join('')}</div>` : empty('A fresh start for your plans.', 'Add your first personal deadline, or follow a published deadline.', 'Add a deadline')}${data.personal.length ? `<div class="progress-panel"><div><strong>${completed} of ${data.personal.length}</strong><p>personal deadlines completed</p></div><progress value="${completed}" max="${data.personal.length}" aria-label="Completed deadlines"></progress></div>` : ''}</section><div>${calendarWidget()}<div class="breathing-room"><span aria-hidden="true">✧</span><h3>One small step is still a step.</h3><p>A little planning today gives tomorrow a little more breathing room.</p></div></div></div><div class="dashboard-grid"><section class="panel">${panelHeader('Coming up next', 'Keep these dates in the corner of your eye.', 'Open calendar', 'calendar')}${soon.length ? soon.map((d) => `<div class="upnext-card">${dateTile(d)}<div><h3>${esc(d.title)}</h3><p>${statusText(d)} · ${esc(d.department || d.category || 'Personal')}</p></div></div>`).join('') : empty('A little breathing room.', 'No upcoming dates on your list.', '', '')}</section><section class="panel">${panelHeader('Published deadlines', 'Useful dates to keep on your radar.', 'Explore', 'government')}${
    data.government.length
      ? data.government
          .slice(0, 2)
          .map(
            (d) =>
              `<div class="upnext-card">${dateTile(d)}<div><h3>${esc(d.title)}</h3><p>${esc(d.department || 'Published deadline')} · ${displayDate(d.due_date)}</p></div></div>`,
          )
          .join('')
      : empty(
          'Nothing published yet.',
          'Deadlines shared by your administrator will appear here.',
          '',
          '',
        )
  }</section></div>`;
}
function filters() {
  return `<div class="filterbar"><label>Search deadlines<input id="search" type="search" value="${esc(query)}" placeholder="Search a title, note or department" maxlength="120"></label><label>Priority<select id="priority-filter"><option value="all">All priorities</option>${['high', 'medium', 'low'].map((v) => `<option value="${v}" ${priority === v ? 'selected' : ''}>${titleCase(v)}</option>`).join('')}</select></label>${view === 'government' ? '' : `<label>Status<select id="status-filter"><option value="all">All statuses</option>${['pending', 'in_progress', 'completed', 'overdue'].map((v) => `<option value="${v}" ${status === v ? 'selected' : ''}>${titleCase(v)}</option>`).join('')}</select></label>`}<button class="button" data-action="csv">${icon('download')} Export CSV</button><button class="button" data-action="ics">${icon('calendar')} Calendar file</button></div>`;
}
function personal() {
  const rows = filtered(),
    pages = Math.max(1, Math.ceil(rows.length / 10));
  page = Math.min(page, pages);
  return `<section class="panel">${panelHeader('Your personal deadlines', 'A little organization goes a long way.')}${filters()}<p class="list-caption"><span>${rows.length} matching deadlines</span><span>Sorted by due date</span></p>${
    rows.length
      ? rows
          .slice((page - 1) * 10, page * 10)
          .map(deadlineRow)
          .join('')
      : empty(
          'Nothing on this list yet.',
          query
            ? 'Try another search or clear your filters.'
            : 'Add a date you want to keep in sight.',
          query ? 'Clear filters' : 'Add a deadline',
          query ? 'clear-filters' : 'new',
        )
  }<div class="pagination"><button class="button" data-action="previous" ${page === 1 ? 'disabled' : ''}>← Previous</button><span>Page ${page} of ${pages}</span><button class="button" data-action="next" ${page === pages ? 'disabled' : ''}>Next →</button></div></section>`;
}
function government() {
  const rows = filtered(),
    admin = data.user.is_admin;
  return `${filters()}<p class="feed-note">These deadlines are published by your administrator. Source links help you confirm requirements and any changes. A subscription adds a deadline to your calendar and configured reminders.</p><div class="feed-grid">${rows.length ? rows.map((d) => `<article class="panel feed-card"><div class="feed-heading"><span class="department-icon">${icon('building')}</span><span>${esc(d.department)}</span>${priorityBadge(d)}</div><h3>${esc(d.title)}</h3><p>${esc(d.description || 'Open the source for application details.')}</p><div class="meta"><span>${icon('calendar')}</span><span>${displayDate(d.due_date)}</span><span>· ${statusText(d)}</span></div><div class="feed-actions">${admin ? `<button class="button primary" data-action="edit-government" data-id="${esc(d.id)}">Edit deadline</button><button class="button danger" data-action="delete-government" data-id="${esc(d.id)}">Delete</button><span class="small muted">${d.subscriber_count || 0} following</span>` : `<button class="button ${d.subscribed ? '' : 'primary'}" data-action="subscribe" data-id="${esc(d.id)}">${d.subscribed ? 'Following ✓' : 'Follow deadline'}</button>`}${d.source_url && /^https:\/\//i.test(d.source_url) ? `<a class="button quiet" href="${esc(d.source_url)}" target="_blank" rel="noopener noreferrer">Open source ${icon('arrow')}</a>` : ''}</div></article>`).join('') : `<section class="panel">${empty('Nothing published yet.', 'Deadlines shared by your administrator will appear here.', admin ? 'Publish a deadline' : '', admin ? 'new' : '')}</section>`}</div>`;
}
function calendarView() {
  const entries = userEntries().filter((d) => d.due_date === selectedDate);
  return `<div class="calendar-layout">${calendarWidget(true)}<section class="panel">${panelHeader(displayDate(selectedDate), 'Your plans for this day.')}<div class="list">${entries.length ? entries.map(deadlineRow).join('') : empty('A little breathing room.', 'Nothing scheduled for this day.', '', '')}</div></section></div>`;
}
function reminders() {
  return `<div class="notice">Reminders are sent only to verified contacts with an enabled preference. A separate reminder worker must be running. This history shows actual attempts; following a deadline never submits an application or makes a payment.</div><section class="panel">${panelHeader('Delivery history', 'Your latest 100 reminder attempts.')}${data.notifications.length ? data.notifications.map((d) => `<article class="delivery-row"><div><strong>${esc(d.title)}</strong><small>Due ${displayDate(d.due_date)} · ${esc(d.channel)}</small></div><span class="badge ${d.status === 'sent' ? 'low' : d.status === 'failed' ? 'high' : 'medium'}">${esc(titleCase(d.status))}</span><span class="small muted">${esc(String(d.created_at || '').slice(0, 10))}</span></article>`).join('') : empty('No delivery attempts yet.', 'Enable a verified channel in Settings and start the reminder worker.', 'Open settings', 'settings')}</section>`;
}
function settings() {
  const u = data.user;
  if (u.is_admin)
    return `<section class="panel">${panelHeader('Administrator workspace', 'Publish useful dates from Government and keep source links up to date.')}<p class="muted">${esc(u.email)}</p><p class="muted">Both native desktop and web use this same publishing account. Your changes appear on the next workspace refresh.</p></section>`;
  return `<div class="settings-grid"><section class="panel">${panelHeader('Your account', 'A few details to make this feel like yours.')}<form id="profile-form"><label>Display name<input name="name" value="${esc(u.name)}" maxlength="80" required></label><label>Email<input value="${esc(u.email)}" readonly></label>${u.phone ? `<label>Phone<input value="${esc(u.phone)}" readonly></label>` : ''}<button class="button primary" type="submit">Save name</button></form></section><section class="panel">${panelHeader('Contact verification', 'Keep your reminders pointed at the right place.')}${['email', 'sms'].map((c) => `<div class="contact-row"><div><strong>${c === 'email' ? 'Email' : 'SMS'}</strong><small>${u[c === 'email' ? 'email_verified' : 'phone_verified'] ? 'Verified' : 'Verification needed'} · ${data.delivery[c] ? 'Provider configured' : 'Provider not configured'}</small></div><button class="button" data-action="verify" data-id="${c}" ${c === 'sms' && !u.phone ? 'disabled' : ''}>Verify ${c === 'email' ? 'email' : 'phone'}</button></div>`).join('')}<p>Verification requires a configured delivery provider. Add your phone number during signup if you want SMS reminders.</p></section><section class="panel">${panelHeader('A timely little nudge', 'Choose how you’d like to hear from AlertMe.')}<form id="preferences-form"><label class="check-row"><input name="email" type="checkbox" ${u.preferences?.email ? 'checked' : ''}>Email reminders</label><label class="check-row"><input name="sms" type="checkbox" ${u.preferences?.sms ? 'checked' : ''}>SMS reminders</label><p>Verify a contact before enabling its channel. Your operator needs to keep the reminder worker running.</p><button class="button primary" type="submit">Save reminder preferences</button></form></section><section class="panel">${panelHeader('Change password', 'You’ll sign in again after updating your password.')}<form id="password-form"><label>Current password<input type="password" name="current_password" autocomplete="current-password" required maxlength="128"></label><label>New password<input type="password" name="new_password" autocomplete="new-password" minlength="10" maxlength="128" required></label><p>Use 10–128 characters, including a letter and a number.</p><button class="button" type="submit">Update password</button></form></section></div>`;
}
function renderAccount() {
  if (!data) return;
  const admin = data.user.is_admin;
  $('account-name').textContent = data.user.name;
  $('account-role').textContent = admin ? 'Administrator' : 'Personal account';
  $('avatar').textContent = $('top-avatar').textContent = (data.user.name || 'Y')
    .slice(0, 1)
    .toUpperCase();
}
function render() {
  if (!data) return;
  const admin = data.user.is_admin;
  if (admin && ['overview', 'personal', 'reminders'].includes(view)) view = 'government';
  document.querySelectorAll('[data-view]').forEach((a) => {
    a.hidden = admin && ['overview', 'personal', 'reminders'].includes(a.dataset.view);
    a.classList.toggle('active', a.dataset.view === view);
    if (a.dataset.view === view) a.setAttribute('aria-current', 'page');
    else a.removeAttribute('aria-current');
  });
  renderAccount();
  $('crumb').textContent = view === 'personal' ? 'My deadlines' : titleCase(view);
  $('page-title').textContent = config[view][0];
  $('page-subtitle').textContent = config[view][1];
  $('new-deadline').hidden =
    ['settings', 'reminders'].includes(view) || (admin && view !== 'government');
  $('new-deadline').innerHTML = icon('plus') + (admin ? 'Publish deadline' : 'New deadline');
  $('view').innerHTML =
    view === 'overview'
      ? overview()
      : view === 'personal'
        ? personal()
        : view === 'government'
          ? government()
          : view === 'calendar'
            ? calendarView()
            : view === 'reminders'
              ? reminders()
              : settings();
  document.title = `${$('crumb').textContent} — AlertMe`;
}
const options = (values, current) =>
  values
    .map(
      (v) =>
        `<option value="${esc(v)}" ${v === current ? 'selected' : ''}>${titleCase(v)}</option>`,
    )
    .join('');
const field = (name, label, value = '', type = 'text', extra = '', wide = false) =>
  `<label class="${wide ? 'wide' : ''}">${label}<input type="${type}" name="${name}" value="${esc(value)}" ${extra}></label>`;
function openEditor(title, fields, callback, save = 'Save deadline') {
  $('editor-title').textContent = title;
  $('editor-fields').innerHTML = `<div class="form-grid">${fields}</div>`;
  $('editor-error').textContent = '';
  $('editor-save').textContent = save;
  $('editor-save').disabled = false;
  editorSubmit = callback;
  $('editor').showModal();
}
function editDeadline(item = null, government = data.user.is_admin) {
  const d = item || {
    due_date: view === 'calendar' ? selectedDate : today(),
    priority: 'medium',
    category: 'Personal',
    status: 'pending',
    reminder_days: [7, 3, 1, 0],
  };
  const fields =
    field('title', 'Title', d.title || '', 'text', 'required maxlength="120"', true) +
    field(
      'due_date',
      'Due date',
      d.due_date,
      'date',
      'required min="1900-01-01" max="2199-12-31"',
    ) +
    `<label>Priority<select name="priority" aria-label="Priority">${options(['low', 'medium', 'high'], d.priority)}</select></label>` +
    (government
      ? field(
          'department',
          'Department',
          d.department || '',
          'text',
          'required maxlength="120"',
          true,
        ) +
        field(
          'source_url',
          'Source URL',
          d.source_url || '',
          'url',
          'placeholder="https://official-source.example" maxlength="500"',
          true,
        )
      : `<label>Category<select name="category" aria-label="Category">${options(['Personal', 'Education', 'Finance', 'Health', 'Work', 'Other'], d.category)}</select></label><label>Status<select name="status" aria-label="Status">${options(['pending', 'in_progress', 'completed'], d.status)}</select></label>` +
        field(
          'reminder_days',
          'Reminder days',
          d.reminder_days.join(', '),
          'text',
          'maxlength="30"',
          true,
        ) +
        '<p class="muted wide">Days before the due date, separated by commas. 0 means the due date. Leave empty for no delivery reminders.</p>') +
    `<label class="wide">Notes<textarea name="description" maxlength="3000">${esc(d.description || '')}</textarea></label>`;
  openEditor(
    item ? 'Edit deadline' : government ? 'Publish deadline' : 'New deadline',
    fields,
    async (f) => {
      if (!government) {
        const values = f.reminder_days
          .split(',')
          .map((v) => v.trim())
          .filter(Boolean);
        if (values.some((v) => !/^\d+$/.test(v)))
          throw new Error('Use comma-separated whole numbers for reminder days.');
        f.reminder_days = values.map(Number);
      }
      const path = government
        ? '/admin/api/government-deadlines' + (item ? '/' + encodeURIComponent(item.id) : '')
        : item
          ? pathFor(item)
          : '/api/personal-deadlines';
      await api(path, { method: item ? 'PUT' : 'POST', value: f });
      if (!item && !government) {
        view = 'personal';
        location.hash = 'personal';
      }
      await loadWorkspace();
    },
    government ? 'Publish deadline' : 'Save deadline',
  );
}
function findEntry(id, storage) {
  return [...data.personal, ...data.government].find(
    (d) => d.id === id && (!storage || d.storage === storage),
  );
}
function download(content, type, name) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function exportCSV() {
  const rows = filtered(),
    cell = (value) =>
      `"${String(value ?? '')
        .replace(/^\s*[=+\-@]/, (m) => "'" + m)
        .replaceAll('"', '""')}"`;
  download(
    [
      'Title,Due date,Priority,Status,Category,Type',
      ...rows.map((d) =>
        [d.title, d.due_date, d.priority, d.status, d.category, d.storage].map(cell).join(','),
      ),
    ].join('\r\n'),
    'text/csv;charset=utf-8',
    `alertme-${today()}.csv`,
  );
  toast('Matching deadlines exported.');
}
function exportCalendar() {
  const escape = (value) =>
      String(value || '')
        .replaceAll('\\', '\\\\')
        .replaceAll('\r', '')
        .replaceAll('\n', '\\n')
        .replaceAll(',', '\\,')
        .replaceAll(';', '\\;'),
    lines = [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//AlertMe//Deadline workspace//EN',
      'CALSCALE:GREGORIAN',
    ];
  for (const d of filtered()) {
    const end = new Date(d.due_date + 'T12:00:00Z');
    if (!Number.isFinite(+end)) continue;
    end.setUTCDate(end.getUTCDate() + 1);
    lines.push(
      'BEGIN:VEVENT',
      `UID:${d.storage}-${d.id}@alertme.local`,
      'DTSTAMP:' +
        new Date()
          .toISOString()
          .replace(/[-:]/g, '')
          .replace(/\.\d{3}Z$/, 'Z'),
      'DTSTART;VALUE=DATE:' + d.due_date.replaceAll('-', ''),
      'DTEND;VALUE=DATE:' + end.toISOString().slice(0, 10).replaceAll('-', ''),
      'SUMMARY:' + escape(d.title),
      'DESCRIPTION:' + escape(d.description),
      'END:VEVENT',
    );
  }
  lines.push('END:VCALENDAR');
  const folded = [];
  for (const line of lines) {
    let value = '';
    for (const c of line) {
      if (new TextEncoder().encode(value + c).length > 74) {
        folded.push(value);
        value = ' ';
      }
      value += c;
    }
    folded.push(value);
  }
  download(folded.join('\r\n') + '\r\n', 'text/calendar;charset=utf-8', `alertme-${today()}.ics`);
  toast('Calendar file exported.');
}
const actions = {
  new: () => editDeadline(),
  edit: (id, storage) => editDeadline(findEntry(id, storage), false),
  'edit-government': (id) => editDeadline(findEntry(id, 'government'), true),
  complete: async (id, storage) => {
    const d = findEntry(id, storage);
    await api(pathFor(d), {
      method: 'PUT',
      value: { status: d.status === 'completed' ? 'pending' : 'completed' },
    });
    await loadWorkspace();
  },
  delete: async (id, storage) => {
    const d = findEntry(id, storage);
    if (confirm(`Delete “${d.title}”? This cannot be undone.`)) {
      await api(pathFor(d), { method: 'DELETE' });
      await loadWorkspace();
      toast('Deadline deleted.');
    }
  },
  'delete-government': async (id) => {
    if (confirm('Delete this published deadline? This cannot be undone.')) {
      await api('/admin/api/government-deadlines/' + encodeURIComponent(id), { method: 'DELETE' });
      await loadWorkspace();
      toast('Published deadline deleted.');
    }
  },
  subscribe: async (id) => {
    const d = findEntry(id, 'government');
    await api('/api/government-deadlines/' + encodeURIComponent(id) + '/subscribe', {
      method: 'POST',
      value: { subscribed: !d.subscribed },
    });
    await loadWorkspace();
    toast(d.subscribed ? 'Unfollowed deadline.' : 'Deadline added to your calendar.');
  },
  'prev-month': () => changeMonth(-1),
  'next-month': () => changeMonth(1),
  'select-date': (value) => {
    selectedDate = value;
    view = 'calendar';
    location.hash = 'calendar';
    render();
  },
  previous: () => {
    page--;
    render();
  },
  next: () => {
    page++;
    render();
  },
  'clear-filters': () => {
    query = '';
    priority = status = 'all';
    page = 1;
    render();
  },
  csv: exportCSV,
  ics: exportCalendar,
  settings: () => (location.hash = 'settings'),
  verify: async (channel) => {
    await api('/api/me/verification', { method: 'POST', value: { channel } });
    openEditor(
      'Verify your contact',
      field(
        'code',
        '6-digit code',
        '',
        'text',
        'required pattern="[0-9]{6}" maxlength="6" inputmode="numeric"',
        true,
      ),
      async (f) => {
        await api('/api/me/verification', { method: 'PUT', value: { channel, code: f.code } });
        await loadWorkspace();
      },
      'Verify contact',
    );
  },
};
function changeMonth(step) {
  const date = new Date(calendarMonth + '-01T12:00:00');
  date.setMonth(date.getMonth() + step);
  if (date.getFullYear() < 1900 || date.getFullYear() > 2199) return;
  calendarMonth = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
  render();
}
$('auth-switch').addEventListener('click', () => {
  loadSerial++;
  signup = !signup;
  $('name-label').hidden = $('phone-label').hidden = $('password-hint').hidden = !signup;
  $('auth-name').required = signup;
  $('admin-label').hidden = signup;
  $('auth-admin').checked = false;
  $('auth-title').textContent = signup ? 'Make room for what matters.' : 'Good to see you.';
  $('auth-subtitle').textContent = signup
    ? 'Create your connected deadline workspace.'
    : 'Sign in to pick up where you left off.';
  $('auth-submit').textContent = signup ? 'Create account' : 'Sign in';
  $('switch-label').textContent = signup ? 'Already have an account?' : 'New here?';
  $('auth-switch').textContent = signup ? 'Sign in' : 'Create an account';
  $('auth-password').autocomplete = signup ? 'new-password' : 'current-password';
  $('auth-error').textContent = '';
});
$('auth-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  loadSerial++;
  $('auth-submit').disabled = true;
  $('auth-error').textContent = '';
  try {
    const identifier = $('auth-identifier').value.trim(),
      password = $('auth-password').value;
    const path = signup ? '/signup' : $('auth-admin').checked ? '/auth/api/admin/login' : '/login';
    const value = signup
      ? { name: $('auth-name').value, email: identifier, phone: $('auth-phone').value, password }
      : $('auth-admin').checked
        ? { email: identifier, password }
        : { identifier, password };
    await api(path, { method: 'POST', value });
    $('auth-password').value = '';
    view = Object.hasOwn(config, location.hash.slice(1)) ? location.hash.slice(1) : 'overview';
    await loadWorkspace();
  } catch (error) {
    $('auth-error').textContent = error.message;
  } finally {
    $('auth-submit').disabled = false;
  }
});
$('editor-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  $('editor-save').disabled = true;
  $('editor-error').textContent = '';
  try {
    await editorSubmit(Object.fromEntries(new FormData(e.currentTarget)));
    $('editor').close();
    toast('Saved to your workspace.');
  } catch (error) {
    $('editor-error').textContent = error.message;
  } finally {
    $('editor-save').disabled = false;
  }
});
document
  .querySelectorAll('[data-close]')
  .forEach((b) => b.addEventListener('click', () => $('editor').close()));
$('new-deadline').addEventListener('click', () => editDeadline());
$('refresh').addEventListener('click', loadWorkspace);
$('sign-out').addEventListener('click', async () => {
  try {
    await api('/logout', { method: 'POST', value: {} });
    showAuth('You have signed out.');
  } catch (error) {
    showError(error.message);
  }
});
$('view').addEventListener('click', async (e) => {
  const button = e.target.closest('[data-action]');
  if (!button || button.disabled) return;
  button.disabled = true;
  try {
    await actions[button.dataset.action]?.(button.dataset.id, button.dataset.storage);
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
  }
});
$('view').addEventListener('input', (e) => {
  if (e.target.id === 'search') {
    query = e.target.value;
    page = 1;
    const start = e.target.selectionStart;
    render();
    $('search').focus();
    $('search').setSelectionRange(start, start);
  }
});
$('view').addEventListener('change', (e) => {
  if (e.target.id === 'priority-filter') priority = e.target.value;
  else if (e.target.id === 'status-filter') status = e.target.value;
  else return;
  page = 1;
  render();
});
$('view').addEventListener('submit', async (e) => {
  e.preventDefault();
  const button = e.target.querySelector('button[type=submit]');
  if (!button) return;
  const owner = data?.user?.id;
  button.disabled = true;
  try {
    const form = Object.fromEntries(new FormData(e.target));
    if (e.target.id === 'password-form') {
      await api('/api/me/password', { method: 'POST', value: form });
      showAuth('Password changed. Sign in again.');
    } else if (e.target.id === 'preferences-form') {
      const result = await api('/api/me', {
        method: 'PUT',
        value: {
          preferences: {
            email: e.target.elements.email.checked,
            sms: e.target.elements.sms.checked,
          },
        },
      });
      if (!data || data.user.id !== owner) return;
      data.user.preferences = result.preferences;
      toast('Reminder preferences saved.');
    } else if (e.target.id === 'profile-form') {
      const result = await api('/api/me', { method: 'PUT', value: { name: form.name } });
      if (!data || data.user.id !== owner) return;
      data.user.name = result.name;
      e.target.elements.name.value = result.name;
      renderAccount();
      toast('Name saved.');
    }
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
  }
});
function closeMenu() {
  const wasOpen = $('sidebar').classList.contains('open');
  $('sidebar').classList.remove('open');
  $('menu-toggle').setAttribute('aria-expanded', 'false');
  return wasOpen;
}
$('menu-toggle').addEventListener('click', () => {
  const open = $('sidebar').classList.toggle('open');
  $('menu-toggle').setAttribute('aria-expanded', String(open));
  if (open) document.querySelector('nav a.active')?.focus();
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && closeMenu()) $('menu-toggle').focus();
});
document.addEventListener('click', (e) => {
  if (!$('sidebar').contains(e.target) && !$('menu-toggle').contains(e.target)) closeMenu();
});
window.addEventListener('hashchange', () => {
  const target = location.hash.slice(1);
  view = Object.hasOwn(config, target) ? target : 'overview';
  query = '';
  priority = status = 'all';
  page = 1;
  closeMenu();
  render();
  if (data) $('main').focus({ preventScroll: true });
});
window.addEventListener('focus', () => {
  if (data && view !== 'settings' && !$('editor').open) loadWorkspace();
});
setInterval(() => {
  if (data && !document.hidden && !$('editor').open && view !== 'settings') loadWorkspace();
}, 60000);
loadWorkspace();
