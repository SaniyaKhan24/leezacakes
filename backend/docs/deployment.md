# Deployment prerequisites (not performed)

Target strategy: Linux Gunicorn WSGI behind a trusted TLS reverse proxy.
Windows development uses runserver. ASGI entry point exists, but choosing an ASGI
server is deferred until needed. There is no automated deployment workflow.

Supply actual DJANGO_SECRET_KEY (random >=50 characters), DJANGO_ALLOWED_HOSTS
(exact hostnames), HTTPS CORS_ALLOWED_ORIGINS and CSRF_TRUSTED_ORIGINS, and existing
Supabase database variables. Never deploy test.py or production_check.py: they
contain no working database and synthetic fixture configuration.

Set DJANGO_SETTINGS_MODULE=config.settings.production. If TLS terminates upstream,
configure the proxy to strip incoming X-Forwarded-Proto and set its own value;
restrict direct backend access, then enable TRUST_PROXY_SSL_HEADER=True. Otherwise
leave it False. Verify redirects, host rejection and secure cookies end-to-end
before enabling traffic. Health probes must use HTTPS through the trusted ingress.

Install hash-locked runtime requirements plus requirements-linux.txt.
Run manage.py check --deploy --fail-level WARNING with real production settings
in the deployment environment. Synthetic checks prove settings behavior, not
DNS, certificates, ingress or database reachability.

Before any database change: confirm custom-user decision, take/test a backup,
review migration plan and SQL, confirm the target database, arrange rollback and
obtain owner approval. Only after approval:
```powershell
.\.venv\Scripts\python.exe manage.py migrate --settings=config.settings.development
```
This local command uses the existing Supabase configuration. It has NOT been run.
Production migrations must instead explicitly use production settings in the
approved deployment environment. Built-in Django auth/admin/session migrations
are still required before those features can work.

Run collectstatic during the approved release build; serve STATIC_ROOT through
the reverse proxy or object storage. Never serve production media through Django;
choose storage, backup, access controls and upload validation first.
Start Linux WSGI with gunicorn config.wsgi:application after configuring the
environment. Choose worker count/timeouts from load tests, not a guessed value.

Liveness only reports process status. Add protected/internal readiness checks
with bounded DB/cache probes when deployment infrastructure is known; never
expose connection strings or exception details. Add monitoring, alerting,
restore drills, shared throttling cache, email configuration and payment-provider
configuration before implementing those features. Neither live Supabase health
nor a production deployment has been verified here.

References:
- https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
- https://scalar.com/products/api-references/configuration

HSTS scope: HSTS_INCLUDE_SUBDOMAINS and HSTS_PRELOAD default to False for real
configuration. The synthetic deployment profile sets both True solely to validate
the full Django security baseline. Real checks will report W005/W021 until an
owner confirms HTTPS coverage and opts into these settings. Do not enable them
just to silence warnings; review the actual domain and preload consequences.
