# Verification notes

Recorded locally on 2026-11-15 with Python 3.12, PyQt6 6.12, a disposable MongoDB 8
server and Chromium. All provider accounts and records used by the suites are
explicit test fixtures.

| Check | Result |
| --- | --- |
| Ruff checks and formatting | Passed |
| Python compilation | Passed |
| API, native desktop, delivery adapter and export tests | 50 passed |
| Website workflow and layout tests | 21 passed |
| Website sizes | Desktop 1440px, tablet 768px, mobile 390px |
| Native window sizes | 1440×960 and 1024×768 |

The Python suite runs through the real API against MongoDB when
`TEST_MONGODB_URI` points to an explicitly disposable loopback server and
`ALLOW_TEST_DATABASE_RESET=1`. These variables are required for database-backed
tests; no in-memory database substitute is used. The native tests drive actual
PyQt widgets and Qt HTTP requests through
a temporary local server; screenshots use Qt's offscreen platform.

Coverage includes signup, sign-in, ownership, input validation, account/index
compatibility, retained deadline stores, admin publishing, subscriptions, contact
verification, code expiry/attempts/concurrency, password revocation, reminders,
provider failure outcomes, duplicate prevention, exports and native/web record
consistency. Native tests also exercise draft retention, account flows, calendar
navigation, password updates and actual file exports.

Website tests cover account and personal-deadline flows, publishing, following,
calendar dates, verification/preferences, password changes, logout, failed-save
recovery, delayed settings saves with sibling-form draft retention, responsive navigation, keyboard dialogs and axe checks for all six
workspace views. These checks supplement visual review and do not certify every
browser or assistive technology.

Use the commands in README.md to rerun the suites. Run against disposable test
data only; no production records or external notification accounts were used.
Live provider delivery, hosted infrastructure and packaged Windows/macOS
installers require separate validation. CI repeats the checks for the PR commit.
