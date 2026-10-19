# Verification record — 19 October 2026

Engineering foundation implemented. Final complete local pre-push run exited 0.
Production deployment has not been verified.

Executed from backend on Windows, Python 3.12.0:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/pre-push.ps1
```

| Check | Final result |
| --- | --- |
| Hash-locked development installation / pip check | Pass |
| Ruff lint / format | Pass, 217 Python files checked |
| Django test-profile system checks | Pass, no silenced issues |
| Django development-profile checks using existing .env | Pass, no DB connection |
| Synthetic production deployment checks | Pass, warnings treated as failures |
| Migration consistency dry-run | Pass, no changes; database access disabled |
| pytest | 20 passed |
| Branch coverage | 96.97%; minimum 85% |
| OpenAPI schema validation | Pass |
| Bandit | No issues; two narrow documented subprocess annotations |
| Runtime / development / Linux pip-audit | No known vulnerabilities reported |
| Swagger / Scalar CDN assets | HTTP 200; HTML routes reference the schema |
| Workflow YAML parsing / dependency-lock consistency | Pass |
| Git diff whitespace / ignore rules | Pass |
| Local .env secret-value scan of tracked/unignored files | Pass; values never printed |

Earlier failures were investigated: tests corrected their OpenAPI and DRF request
assumptions; Bandit fixture password was replaced with an ephemeral value; Ruff
formatting was completed; dependency download/hash tooling was corrected.
The audit detected vulnerable DRF 3.16.1 and the temporary older pip used for
lock-generation diagnostics. Final locks use DRF 3.17.2 and pip 26.2.1, and the
complete audits pass without ignored vulnerability IDs.

The machine blocks direct PowerShell script execution. The process-only invocation
above was tested; no machine execution-policy setting was changed. The standard
invocation remains .\scripts\pre-push.ps1 on machines allowing local scripts.

Not executed: migrations, database integration or migration-history validation,
browser JavaScript rendering, GitHub-hosted jobs, Linux server execution, and
production deployment. No browser automation tool was available; template/schema
wiring and CDN reachability were checked instead. CI files were validated locally
but were not pushed. Supabase data was not accessed or changed.

Real deployment checks require actual domains, secrets, trusted proxy decisions
and HSTS scope review. Synthetic HSTS settings do not validate real domain coverage.
See deployment.md and security.md for approval steps and GitHub settings.
