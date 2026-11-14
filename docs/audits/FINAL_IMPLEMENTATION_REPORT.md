# First implementation pass — AlertMe

Repository: https://github.com/taksh1507/AlertMe-Government-Deadline-Assistant

Date: 2026-11-14. Branch: `codex/portfolio-security-audit-2026-11-14`.

## Initial condition

Flask/PyQt6 application without an automated regression suite. Local mock tests reproduced cross-user access, ownership mutation, unbounded tokens and model configuration failures (6 failed, 1 passed). Additional review found an admin credential override and a tracked environment file.

## Changes implemented

- Enforce owner-scoped queries for both deadline API families and prevent ownership reassignment through update payloads.
- Require a signing key, expire newly issued JWTs, disable unconfigured admin access, and accept hashed admin credentials.
- Validate authentication input types and malformed deadline IDs.
- Use the configured MongoDB client and database names in both models; no schema or migration changes.
- Disable the interactive debugger and bind the standalone development server to loopback.
- Untrack `.env` without deleting local configuration; add a safe configuration template.
- Add twelve regression tests, a separate backend test dependency manifest, read-only CI workflow and setup/security documentation.

## Files changed

`Alertme/src/backend/app.py`, `Alertme/src/backend/models/deadline.py`,
`Alertme/src/backend/models/personal_deadline.py`, `Alertme/.env` (untracked),
`Alertme/.env.example`, `tests/test_security.py`, `requirements-test.txt`,
`.github/workflows/security-tests.yml`, `README.md`, and the three documents in
`docs/audits/`.

## Verification

- Passed: `python -m pytest tests -q` — 12 passed, 4 datetime deprecation warnings.
- Baseline: first seven new regression cases against original code — 6 failed, 1 passed.
- Failed after remediation: none in this targeted suite.
- Skipped: none in this targeted suite.
- Unverified: full application dependency installation, GUI rendering, live MongoDB, notification/provider integrations, historical secret exposure, CI execution on GitHub and deployment.

No UI redesign, dependency upgrades to the application manifest, database migration, deployment or measured performance optimization was performed in this pass. API paths remain the same; missing ownership now returns 404 and bad IDs return 400. Configuration and token-expiry changes require deployment coordination.

## Remaining work

See `SECURITY_AUDIT.md` for residual risks, rotation guidance and further assessment. This first pass does not complete the full portfolio modernization request and does not establish production readiness.

Pull request: pending creation; see the branch's GitHub pull request for review.
