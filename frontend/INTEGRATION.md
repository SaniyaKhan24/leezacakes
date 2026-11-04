# Leeza Cakes frontend ↔ backend integration

All requests go to the storefront's own origin and are proxied to Django (`next.config.ts` rewrites). Image URLs that Django returns as absolute `/media/...` links are rewritten to the proxied path by `mediaUrl()`.

| Journey step | Endpoints |
| --- | --- |
| Catalogue | `GET /api/v1/catalog/products/`, `/products/<slug>/`, `/categories/` |
| Customisation | `GET /api/v1/customization/products/<slug>/options/` — selections are sent with **global** option and choice ids (`option.option.id`, `choice.choice`) |
| Cart (guest or signed in) | `GET/POST /api/v1/cart/…`, `POST /api/v1/cart/merge/` after sign-in, `POST /cart/confirm-prices/` |
| Accounts | register, email verification (`/auth/verify?uid=&token=`), login/refresh/logout, password reset (`/auth/reset?uid=&token=`), `me`, addresses |
| Pickup slots | `GET /api/v1/orders/pickup-slots/` (lead time from the cart's longest preparation time) |
| Orders | `POST /api/v1/orders/` with `Idempotency-Key`, `GET /api/v1/orders/`, `/orders/<id>/` |
| Payment | `GET /api/v1/payments/orders/<order_id>/` (includes UPI `instructions`), `POST /api/v1/payments/<id>/submissions/` (PNG/JPEG/WebP ≤ 5 MB) |
| Site & enquiries | `GET /api/v1/site/`, `POST /api/v1/enquiries/` |

## Deliberate boundaries

- **Pickup only.** The order contract takes a pickup slot, not a delivery address. Saved addresses can be managed in the account but are not used at checkout yet.
- **No payment gateway.** Customers pay by UPI and upload proof; staff verify it in Django admin, which confirms the order. Sample UPI details in development are clearly flagged as samples.
- **Sample content.** Contact details from `/api/v1/site/` are flagged `is_sample` in development and the UI labels them as such. Production returns `null` for anything not configured.
