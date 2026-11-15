# Contributing

Use Python 3.12+, Node.js 22+ for browser checks, and a supported MongoDB instance.
Install `requirements-test.txt` and the npm lockfile dependencies. Run Ruff,
compilation, Python tests and the browser suite before proposing behavior changes.

Keep native desktop and web behavior aligned through the shared API. Avoid
blocking Qt's event loop with requests, and retain drafts when saving fails.
Validate dates and allowed fields centrally. Use real counts and delivery outcomes,
not fabricated example statistics in application fallbacks.

Tests must use disposable fixture databases. Real-server tests require a loopback
`TEST_MONGODB_URI` plus `ALLOW_TEST_DATABASE_RESET=1` and intentionally reset their
named test databases. Browser contexts and provider fixtures contain synthetic
accounts only. Never commit environment values, personal records or test traces.

Keep public documentation focused on setup, usage, architecture and verified
results. Report sensitive issues through a private maintainer contact or GitHub
private reporting where available.

Preserve the repository's existing non-commercial license.
