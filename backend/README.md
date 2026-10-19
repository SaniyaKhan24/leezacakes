# Leeza Cakes backend

Django 5.2 LTS / DRF, Python 3.12, Supabase PostgreSQL. This is an engineering
foundation, not a verified production deployment. Business apps remain scaffolds.

## Windows setup

From `C:\leezacakes\backend`:
```powershell
# Only create the environment if it is missing:
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements-dev.txt
# Only copy the example if .env is missing:
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe manage.py runserver --settings=config.settings.development
```

Use the latest Python 3.12 patch release. Existing .env and database credentials
were preserved. Supply actual values in the placeholders. A missing development
secret gets an ephemeral key; set a persistent secret for stable sessions.
Development debugging is local only. Never expose runserver publicly.

## One-command checks

```powershell
.\scripts\pre-push.ps1
# Explicit offline mode (not full security verification):
.\scripts\pre-push.ps1 -SkipDependencyAudit
```

The script uses the existing virtual environment, fails immediately and returns a
nonzero exit code on any failure. It never applies migrations or accesses Supabase.
Git hooks can be bypassed; require independent GitHub checks before merging.

Individual commands:
```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe manage.py check --settings=config.settings.test
.\.venv\Scripts\python.exe -m pytest
```

API routes: /api/v1/health/ (liveness), /api/schema/, /api/docs/swagger/,
 /api/docs/scalar/. Documentation is enabled locally and disabled in production
unless API_DOCS_ENABLED=True explicitly opts into public documentation.

See [architecture](docs/architecture.md), [development](docs/development.md),
[security](docs/security.md), and [deployment](docs/deployment.md).
Actual results and unverified deployment areas are recorded in
[verification](docs/verification.md).

If Windows execution policy blocks the script, use this process-only invocation
without changing machine policy:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\pre-push.ps1
```
