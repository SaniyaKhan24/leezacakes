# Leeza Cakes backend

Django 5.2 LTS / DRF, Python 3.12. Production uses Supabase PostgreSQL; local
development can run on SQLite with `DEV_USE_SQLITE=True`. This is an engineering
foundation, not a verified production deployment.

Dependencies live in `requirement/` as version-range manifests (not hash locks):
`base.txt` (runtime), `development.txt` (runtime + lint/test/audit tools) and
`production.txt` (runtime).

## Local setup

Run everything from the `backend/` directory. Only create the virtual environment
and copy `.env.example` if they do not exist yet; never overwrite a working `.env`.

### Linux / macOS

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirement/development.txt
[ -f .env ] || cp .env.example .env
# Without Supabase: use a local SQLite file (backend/db.sqlite3, git-ignored).
export DEV_USE_SQLITE=True
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py runserver
```

### Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirement\development.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Without Supabase: use a local SQLite file (backend\db.sqlite3, git-ignored).
$env:DEV_USE_SQLITE = "True"
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver
```

`manage.py` defaults to `config.settings.development`. You can also put
`DEV_USE_SQLITE=True` in `.env`. It is honoured only by the development settings;
with it, the `DB_*` variables are not needed. Without it, PostgreSQL is required and
startup fails if `DB_NAME`, `DB_USER`, `DB_PASSWORD` or `DB_HOST` is missing (there is
no silent fallback). Production refuses to start with `DEV_USE_SQLITE` set.

A missing development `DJANGO_SECRET_KEY` gets an ephemeral key; set one for stable
sessions. Never expose `runserver` publicly.

### What development configures for you

| Setting | Development default | Notes |
| --- | --- | --- |
| `EMAIL_BACKEND` | console | Verification and password-reset emails, with their links, are printed in the `runserver` output. |
| `FRONTEND_URL` | `http://localhost:3000` | Email links: `/auth/verify?uid=…&token=…` and `/auth/reset?uid=…&token=…`. |
| `ORDER_TAX_RATE` / `ORDER_PRICES_INCLUDE_TAX` | `0` / `True` | Prices are GST-inclusive; orders expose `prices_include_tax`. Outside development checkout is disabled until `ORDER_TAX_RATE` is set. |
| `PAYMENT_UPI_ID` | `leezacakes.sample@example` | Deliberately not a real UPI handle; `is_sample: true` is returned so the UI can say "do not pay". |
| `SITE_*` | Clearly fake contact details | Served by `GET /api/v1/site/` with `is_sample: true`. Unset values are `null` in production. |
| Media | Served at `/media/` while `DEBUG` | Product and category photos. |

See `.env.example` for every variable.

## Demo data

`python manage.py seed_demo` is idempotent and runs only with `DEBUG=True` (or
`--force` for the catalogue part, which never creates accounts). It seeds:

- 5 categories and 14 cakes with variants, SKUs and GST-inclusive prices;
- customisation options (egg preference, message, finishing touches, candles);
- product/category photos from `apps/catalog/seed_assets/products/<slug>.webp`
  (primary), `<slug>-2.webp` (optional second angle) and
  `apps/catalog/seed_assets/categories/<slug>.webp`. Missing files are listed as a
  WARNING; use `--assets-dir` to point at another folder;
- a demo customer and a staff superuser;
- four sample orders for the customer: completed, ready for pickup, payment proof
  waiting for review, and awaiting payment. Re-running does not duplicate them; use
  `--reset-orders` to recreate them.

`python manage.py seed_demo_catalog` seeds only the catalogue and customisations.

Demo credentials (local development only):

| Role | Email | Password |
| --- | --- | --- |
| Customer | `demo@leezacakes.test` | `LeezaDemo!2026` |
| Staff (superuser) | `studio@leezacakes.test` | `LeezaStudio!2026` |

## Customer journey (API)

1. Browse: `GET /api/v1/catalog/products/`, `GET /api/v1/catalog/products/<slug>/`,
   options at `GET /api/v1/customization/products/<slug>/options/`.
2. Guest cart: `POST /api/v1/cart/items/` (session cookie identifies the guest).
3. Register `POST /api/v1/accounts/register/`, open the emailed link (printed in the
   runserver console), which the frontend turns into
   `POST /api/v1/accounts/email/verification/confirm/ {uid, token}`, then
   `POST /api/v1/accounts/login/` and `POST /api/v1/cart/merge/` with the same
   session cookie plus the Bearer token.
4. Pickup: `GET /api/v1/orders/pickup-slots/` lists 14 days of hourly slots (10:00 to
   20:00 IST). The lead time is the larger of 4 hours and the slowest cake's
   preparation time. Checkout rejects any slot that is not an available slot from
   this grid.
5. Checkout: `POST /api/v1/orders/` with an `Idempotency-Key` header.
6. Pay: `GET /api/v1/payments/orders/<order_id>/` returns `instructions` (UPI ID,
   amount, `upi://pay` URI); upload proof with
   `POST /api/v1/payments/<payment_id>/submissions/` (multipart field `evidence`).
7. Track: `GET /api/v1/orders/<order_id>/` shows `status`.

Also: `POST /api/v1/enquiries/` for contact and custom-cake requests (10/hour per
client) and `GET /api/v1/site/` for public contact details.

## Staff workflow in Django admin

Sign in at `http://localhost:8000/admin/` (the "Leeza Cakes Studio" admin).

1. **Payments**: open a payment to see the uploaded proof (thumbnail and full-size
   link served privately to staff with the "Can verify payments" permission).
   Select payments in the list and run **Accept latest proof and verify payment**
   (accepts the pending proof and verifies the full amount due; the order becomes
   *Confirmed*) or **Reject latest proof** (the customer can upload a new one).
2. **Orders**: select orders and run **Start preparing**, **Mark ready for pickup**,
   **Mark completed** or **Cancel**. Every action goes through the same lifecycle
   rules as the API; transitions that are not allowed are reported per order.
3. **Enquiries**: filter new enquiries and mark them contacted or closed.

## Checks

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m pytest
.venv/bin/python scripts/checks.py --skip-dependency-audit   # what CI runs
```

On Windows replace `.venv/bin/python` with `.\.venv\Scripts\python.exe`, or run
`.\scripts\pre-push.ps1`. Tests use an in-memory SQLite database and temporary
directories for uploads; they never touch Supabase or the repository's media folders.
Coverage must stay at or above 85%.

API documentation (development): `/api/schema/`, `/api/docs/swagger/`,
`/api/docs/scalar/`. Health: `/health/live/`, `/health/ready/`.

See [architecture](docs/architecture.md), [development](docs/development.md),
[security](docs/security.md), [deployment](docs/deployment.md) and
[verification](docs/verification.md).
