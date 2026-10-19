# Architecture

config/settings/base.py contains shared configuration; development.py uses the
existing Supabase .env, production.py validates deployment values. ASGI/WSGI
default to production; manage.py defaults to development.

All nine apps are registered with AppConfig and retain migration packages and
existing modules. No business models, services, payment flows or customer
authentication endpoints were invented. Future services perform writes; selectors
perform reads; serializers validate API input. Search queries catalog models,
never duplicate product records. core contains reusable infrastructure only.

The built-in auth.User is retained deliberately: no custom identity requirements
are known. Revisit email login/custom-user requirements BEFORE the first migration
with the owner; changing AUTH_USER_MODEL after migrations is complex. No migration
files were needed or generated.

DRF defaults: session authentication with CSRF protection, authenticated permission,
JSON responses, page size 20, process-local anonymous/user throttles. Health is an
explicit public exception, with no auth or throttle database/cache work.
No API login or client-controlled payment confirmation exists.

test.py and production_check.py use synthetic settings and Django's dummy database
backend. No SQLite replacement and no connection to Supabase. A router prevents
migration-history probing during static consistency checks. Current tests need no
database. This does NOT verify applied migration history, SQL or database behavior.
When models are added, add a separate PostgreSQL integration profile and CI service
with isolated credentials; never point pytest at the development/production DB.
