# Security audit — AlertMe

Date: 2026-11-14. Scope: the standalone Flask backend, deadline models and local regression tests. This is a first remediation pass, not a completed security certification.

| Severity | Component | Finding and remediation | Verification |
| --- | --- | --- | --- |
| Critical | JWT configuration | A predictable fallback signing key allowed tokens to be forged if no secret was configured. Startup now requires a non-placeholder key of at least 32 characters. | Missing-key regression passes. |
| High | Deadline routes and models | Authenticated users could read, update or delete another user's deadlines by ID; update payloads could change ownership. Reads/writes/deletes now include the authenticated owner in the database filter, and updates allow only editable fields. | Both route families tested for cross-user rejection and owner success. |
| High | Admin authentication | Hardcoded admin credentials overrode environment configuration. Removed the override and defaults; login stays disabled without explicit configuration, with support for a Werkzeug password hash. | Unconfigured and configured-hash login tests pass. |
| Medium | Sessions | Access tokens never expired. New tokens now expire after one hour. | Expiry assertion passes. |
| Medium | Login input | Non-string identifiers could reach MongoDB query construction. Login validates string inputs; signup restricts accepted fields. | Query-operator input rejected in regression test. |
| Medium | Configuration | Tracked `.env` encouraged credentials to be committed. It is untracked without deleting the local file; `.env.example` contains no credentials. | Git index inspection; no history rewriting. |
| Medium | Development server | Network-wide interactive debug server was enabled. Standalone development server now uses loopback without debug. | Source inspection; deployment behavior unverified. |

## Verification

`python -m pytest tests -q`: **12 passed**, 4 datetime deprecation warnings. Tests run with a local MongoDB mock and test-only values, not real credentials. The first seven regression cases against original application code produced **6 failures and 1 pass**. Five additional cases were added during remediation.

## Remaining risks and operational steps

- Rotate the JWT signing key and any admin or provider credentials ever used from committed configuration. Old tokens lacking expiry remain valid until signing-key rotation; this PR alone does not revoke them. Review active deployments before rollout.
- Historical secret scanning and credential revocation were not performed. The reviewed `.env` appeared to use placeholders; do not interpret that as proof that historical values were safe.
- Legacy auth blueprints/utilities, notification workflows, CORS policy, rate limiting, data validation and safe error handling still require review. Some API error paths expose exception text.
- Dependency versions in `Alertme/requirements.txt` remain old; full GUI/provider compatibility and vulnerability remediation are outstanding. `requirements-test.txt` deliberately isolates backend regression dependencies from the desktop/provider stack.
- GUI login expiry handling, live MongoDB, SMS/email, Firebase and deployment integration remain unverified. No production operations were performed.
