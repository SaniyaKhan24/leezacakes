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
| `EMAIL_PROVIDER_ENABLED` / `BACKEND_PUBLIC_URL` | `True` / `http://127.0.0.1:8000` | Order notification emails are printed too; staff alert emails link to the Django admin. WhatsApp stays off until configured. |
| `FIELD_ENCRYPTION_KEY` | Fixed local key | Encrypts the WhatsApp secrets saved in admin. Production requires its own key. |
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
7. Track: `GET /api/v1/orders/<order_id>/` shows `status`; updates also arrive in
   `GET /api/v1/notifications/inbox/` (see Notifications & WhatsApp).

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
4. **Alerts**: new orders and payment screenshots pop up as toasts with a chime
   on any admin page, and in the **Alerts** menu next to the user links.

## Notifications & WhatsApp

Every order event creates a row in `apps.notifications`. The copy (title, body, link,
email and WhatsApp text) is rendered from the stored payload by
`apps/notifications/messages.py` each time it is shown or sent, so wording can change
without touching old rows.

| Event | Who | In-app title (example) | Email | WhatsApp template |
| --- | --- | --- | --- | --- |
| `order_created` | customer | Order LZ-… received | yes | `order_received` |
| `payment_submitted` | customer | We've got your payment screenshot | yes | `payment_received` |
| `payment_rejected` | customer | Please re-upload your payment screenshot | yes | `payment_rejected` |
| `payment_verified` | customer | Payment verified for LZ-… | no (covered by `order_confirmed`) | none |
| `order_confirmed` | customer | Order LZ-… is confirmed | yes | `order_confirmed` |
| `preparing` | customer | We're baking order LZ-… | yes | none (optional) |
| `ready` | customer | Order LZ-… is ready for pickup | yes | `order_ready` |
| `completed` | customer | Enjoy your cake! | yes | `order_completed` |
| `staff_order_created` | staff | New order LZ-… · ₹2,340 | staff alert emails | `staff_new_order` |
| `staff_payment_submitted` | staff | Payment screenshot for LZ-… · ₹2,340 | staff alert emails | `staff_payment_submitted` |
| `staff_whatsapp_message` | staff | WhatsApp from Aanya Rao | no (in-app only) | none |

### Background delivery (the notification worker)

Email and WhatsApp are **not** sent during the customer's request. When an event is
recorded, its deliveries are written to the database in the same transaction as the
order or payment (an *outbox*): a rolled-back checkout queues nothing, and a slow or
failing provider can never slow down checkout. A separate process sends them:

```bash
python manage.py run_notification_worker          # runs until stopped (SIGTERM/Ctrl-C)
python manage.py run_notification_worker --once   # send what is due, then exit
```

Run it next to the web server in every environment (in development, a second terminal
with the same environment variables as `runserver`). It needs no Redis or broker: on
PostgreSQL it claims rows with `SELECT … FOR UPDATE SKIP LOCKED`, so you can run more
than one, and each claim is a short lease (`NOTIFICATION_LEASE_SECONDS`, default 120)
so a crashed worker's rows are picked up again. Failures that can clear on their own
(SMTP outage, network errors, WhatsApp 429/5xx) are retried after 1 min, 5 min,
30 min, then 2 h (`NOTIFICATION_RETRY_DELAYS`, seconds) up to
`NOTIFICATION_MAX_ATTEMPTS` (default 5). Permanent rejections (a WhatsApp template or
number Meta refuses) fail at once. **Delivery attempts** in the admin show each row's
status, attempts, next try and last error, and **Retry now** queues anything unsent.

In-app notifications (the bell, the admin alerts) do not depend on the worker: they
appear as soon as the order or payment is saved.

Channels:

- **In-app inbox** (always): `GET /api/v1/notifications/inbox/?page=1&page_size=20`,
  `GET /api/v1/notifications/inbox/unread-count/` and
  `POST /api/v1/notifications/inbox/read/` with `{"ids": [..]}` or `{"all": true}`.
  Both GET endpoints accept `?audience=customer|staff`; the list also takes
  `?unread=true`. Every active staff user gets their own staff row (own read state).
- **Django admin live alerts**: while signed in to `/admin/`, staff see an **Alerts**
  link with an unread badge. The page polls the unread count every 15 s and, for each
  new order or payment screenshot, shows a toast, plays a short chime and (after
  **Enable desktop alerts**) shows a browser notification. The chime needs one click on
  the page first (browser autoplay rules). **Notifications** and **Delivery attempts**
  in the admin show what was sent, skipped or failed, and why.
- **Email** (`EMAIL_PROVIDER_ENABLED=True`; the default in development, printed by the
  console backend): customers at the order email (else the account email), staff at
  the staff alert emails set in the admin (WhatsApp & alert settings). Customer links use `FRONTEND_URL`, staff links
  `BACKEND_PUBLIC_URL` (development default `http://127.0.0.1:8000`). In production
  set `EMAIL_BACKEND`/`EMAIL_HOST`/`EMAIL_PORT`/`EMAIL_HOST_USER`/
  `EMAIL_HOST_PASSWORD`/`EMAIL_USE_TLS` and `DEFAULT_FROM_EMAIL`.
- **WhatsApp** (switched on in the admin, see below): Meta WhatsApp Cloud API template
  messages to the order phone (else the account phone, normalised to E.164; local
  10-digit numbers get +91) and to the staff WhatsApp numbers set in the admin. These are service
  messages, so they are sent regardless of the marketing opt-ins, but never without a
  phone number.

Until a channel is configured, its delivery attempts are recorded as **skipped** with
the reason (for example `email provider is not configured.` or `No email address (add
staff alert emails in admin).`). Deliveries are sent by the notification worker (see
*Background delivery*); a failing provider is recorded as **failed** with its error and
retried if the failure is temporary. It never affects checkout or uploads, and a sent
delivery is never repeated.

### WhatsApp: everything is set up in Django admin

There are no WhatsApp environment variables. The shop owner manages it all at
**Admin → Notifications → WhatsApp & alert settings** (`/admin/notifications/whatsappsettings/`):

- **Chat button**: the public number behind the website's WhatsApp buttons.
  `GET /api/v1/site/` returns it as `whatsapp` and as digits for `wa.me` links in
  `whatsapp_link_number` (`null` until it is set; `seed_demo` sets the sample
  `+91 90000 00000` in development).
- **Sending (Cloud API)**: on/off switch, phone number ID, WhatsApp Business Account ID,
  access token, Graph API version (default `v26.0`) and template language.
- **Staff alerts**: WhatsApp numbers and email addresses alerted about new orders and
  payment screenshots.
- **Webhook**: the callback URL and verify token to paste into Meta, and the app secret
  that signs Meta's calls.
- **Templates**: which Meta template each event uses, whether it is on, and its Meta
  status (approved, pending, rejected, paused, disabled, or not in Meta).

The access token and app secret are encrypted in the database with
`FIELD_ENCRYPTION_KEY` (Fernet). Production refuses to start without that key;
development and tests use a fixed local key. The admin never shows a saved secret
again: it only says "•••• saved". Leave the field blank to keep the saved value, tick
**Remove** to delete it. If the key is lost or changed, the page says the secret cannot
be decrypted, and you enter it again. To rotate the key, put the new key first
(`FIELD_ENCRYPTION_KEY=new,old`) and re-enter the secrets.

Settings are cached for up to 15 s per process, so the web server and the worker pick
up a change within seconds.

#### Step by step

1. **Create the Meta side.** Create a Meta Business portfolio at
   <https://business.facebook.com>. At <https://developers.facebook.com/apps>, create an
   app of type **Business** and add the **WhatsApp** product. Under **WhatsApp → API
   Setup**, add and verify the shop's WhatsApp Business number. It cannot stay
   registered in the WhatsApp phone app at the same time.
2. **Copy the IDs.** On the **API Setup** page, copy the **Phone number ID** (not the
   phone number) and the **WhatsApp Business Account ID** into the admin fields with the
   same names.
3. **Create a permanent token.** In Business settings → **Users → System users**, add an
   admin system user and assign it the app and the WhatsApp account. Then **Generate
   token** with `whatsapp_business_messaging` and `whatsapp_business_management` and
   expiry "Never", and paste it into **Access token**. The temporary token on API Setup
   expires after 24 hours.
4. **Save, then press Check connection** (at the top of the page). It shows the display
   number, verified name, quality rating, platform and throughput, or Meta's error.
5. **Press Submit missing templates.** Every enabled template that Meta does not have
   yet is created as a **Utility** template. The page sends the exact body shown in the
   Templates table, with sample values for Meta's review.
6. **Wait for approval** (minutes to a day), then press **Sync template status**.
   Rejected templates show Meta's reason.
7. **Press Send test message** with your own number and an event. It sends that
   template with sample values right away and shows the message id or Meta's error.
   With Meta's test number you can only message numbers on its allowed list.
8. **Tick "Sending enabled" and save.** From now on the notification worker sends order
   updates and staff alerts. Enabling needs the phone number ID and access token.
9. **Connect the webhook** for delivery receipts and customer replies. In the App
   Dashboard → **WhatsApp → Configuration → Webhook**, paste the **Callback URL** and
   **Verify token** shown in the admin. The URL is `BACKEND_PUBLIC_URL` +
   `/api/v1/notifications/whatsapp/webhook/` and must be public HTTPS. Meta calls it
   once to verify. Then subscribe to the **messages** field. Copy **App settings →
   Basic → App secret** into **App secret** in the admin. Without it, every webhook
   call is rejected (403), because each one must carry a valid `X-Hub-Signature-256`.

Template bodies (variables are filled in this order; they live in
`apps/notifications/messages.py` next to the code that fills them, and a test keeps
the two in step):

| Event | Template | Body |
| --- | --- | --- |
| `order_created` | `order_received` | `Hi {{1}}, thank you for ordering from Leeza Cakes! We've received order {{2}} for {{3}}, pickup {{4}}. Please pay by UPI on your order page and upload the screenshot, and we'll confirm your order by hand.` |
| `payment_submitted` | `payment_received` | `Hi {{1}}, we've received your payment screenshot for order {{2}}. We'll match it with our UPI account and confirm your order shortly.` |
| `payment_rejected` | `payment_rejected` | `Hi {{1}}, we couldn't match the payment screenshot for order {{2}} to a UPI payment. Please upload a clear screenshot on your order page showing the amount, date and UTR number.` |
| `order_confirmed` | `order_confirmed` | `Hi {{1}}, your payment is verified and order {{2}} is confirmed for pickup on {{3}}. We'll message you when it's ready.` |
| `preparing` (off by default) | `order_preparing` | `Hi {{1}}, we've started baking order {{2}}. We'll message you when it's ready.` |
| `ready` | `order_ready` | `Hi {{1}}, order {{2}} is ready! Please come by for your pickup slot ({{3}}) and show your order number at the counter.` |
| `completed` | `order_completed` | `Hi {{1}}, thank you for picking up order {{2}}. We hope it made your day special, and we'd love to bake for you again!` |
| `staff_order_created` | `staff_new_order` | `New order {{1}} from {{2}} for {{3}}. Items: {{4}}. Pickup: {{5}}. Payment is pending verification in the studio.` |
| `staff_payment_submitted` | `staff_payment_submitted` | `Payment screenshot uploaded for order {{1}} by {{2}} ({{3}}). Please check the UPI account and verify it in the studio.` |

Customer variables are first name, order number, then total and/or pickup time
(`₹2,340`, `Thu 5 Nov, 12 pm`). Staff variables are order number, customer name,
total, then items and pickup. Renaming a template in the admin is fine, but Meta needs
an approved template with that name and the same variables. Graph API errors appear
on the failed delivery attempt or in the admin message; tokens and secrets are
redacted.

#### Delivery receipts and customer replies

- **Receipts**: when Meta reports a message as delivered or read, **Delivery attempts**
  shows *Delivered at* / *Read at*. If Meta reports it failed (for example, the number
  is not on WhatsApp), the attempt is marked failed with Meta's error.
- **Customer messages** are stored under **Admin → Notifications → WhatsApp
  conversations**, one conversation per customer number. Each conversation is linked to
  the customer's account and latest order by matching the phone number. Every incoming
  message raises an in-app **staff alert** ("WhatsApp from Aanya Rao") with a toast and
  chime in the admin. It is not forwarded by email or WhatsApp, which avoids loops.
  Opening a conversation marks its messages as read.
- **Replying**: WhatsApp allows free-form replies only within **24 hours** of the
  customer's last message. Inside that window the conversation page has a **Reply**
  box. Outside it, the page explains why and offers to send an approved order template,
  filled in from the linked order. Replies are stored in the conversation, and their
  delivery and read receipts update it too.

The provider is chosen per installation (`meta_cloud`). Another BSP can be added in
`apps/notifications/channels/whatsapp.py` by implementing the same methods
(`send_template`, `send_text`, and the account calls used by the admin tools) and
registering it in `PROVIDERS`.

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
