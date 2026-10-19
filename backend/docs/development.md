# Development and verification

Python 3.12 is the lint and CI target. Upgrade the installed 3.12.0 to a current
3.12 patch release separately. Run all commands from backend; activation is optional.
Use .venv/Scripts/python.exe explicitly on Windows.

.env resolves relative to backend, independent of current directory. Process
environment values override .env. Keep the working DB_NAME, DB_USER, DB_PASSWORD,
DB_HOST, DB_PORT and DB_SSLMODE. TLS require is the baseline; verify-full plus
appropriate provider CA configuration should be evaluated for certificate identity
verification. Transaction-pool compatibility disables server-side cursors.

requirements.in / requirements-dev.in / requirements-linux.in express intentional
constraints. Generated .txt files pin transitive versions and hashes. Linux adds
the separate gunicorn lock because Windows resolution omits the runtime marker.
Install dev tools from requirements-dev.txt; Linux deployments install both
requirements.txt and requirements-linux.txt with --require-hashes.

Update locks with the same Python/pip-tools versions from the dev lock:
```powershell
.\.venv\Scripts\python.exe -m piptools compile --upgrade --generate-hashes --allow-unsafe --strip-extras -o requirements.txt requirements.in
.\.venv\Scripts\python.exe -m piptools compile --upgrade --generate-hashes --allow-unsafe --strip-extras -o requirements-dev.txt requirements-dev.in
.\.venv\Scripts\python.exe -m piptools compile --upgrade --generate-hashes --allow-unsafe --strip-extras -o requirements-linux.txt requirements-linux.in
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements-dev.txt
.\scripts\pre-push.ps1
```
Review all three lock diffs and run Linux/Windows CI. Platform markers/wheel
availability mean the lock is not a claim of bit-identical cross-platform builds.

Pre-push order: package compatibility, Ruff lint/format, Django checks, synthetic
production deploy checks, migration consistency, pytest with branch coverage
(85% minimum), schema validation, Bandit, online dependency audit.
Only generated migrations are omitted from coverage; application/configuration
code remains measured. Existing empty scaffold files do not add covered statements.

The schema is validated by drf-spectacular. Swagger and Scalar reference the same
/api/schema/ endpoint. Browser assets use pinned external CDN versions; Internet
access is required to render the interactive UI. CI tests HTML/schema wiring, not
browser JavaScript rendering. Vendor reviewed assets before an offline deployment.

For later model changes, generate migrations only against an explicitly isolated
development PostgreSQL environment, inspect SQL and migration files, and seek
approval before applying to Supabase. The pre-push dry-run never writes migrations.

Lock compiler: pip-tools 7.6.2 with pip 26.2.1 is pinned and audited. Hash lookup
may fall back to downloading distribution files; allow time on a first lock build.
Subsequent builds reuse recorded hashes. --allow-unsafe is pip-tools terminology
for including packaging tools such as pip/setuptools in the hash lock; it does
not disable package integrity or vulnerability checks.