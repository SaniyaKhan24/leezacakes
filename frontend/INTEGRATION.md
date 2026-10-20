# Leeza Cakes frontend integration

## Implemented against the existing backend

- Catalogue: public categories, products, variants, images, featured products, and documented search filters.
- Customization: product options and choices, selection validation, and cart selection submission.
- Accounts: register, login, logout, access-token refresh, profile context, saved-address reads, and guest-cart merge after login.
- Cart: guest/authenticated retrieval, add, quantity update, removal, server price confirmation, and checkout validation.
- Orders: authenticated creation with an `Idempotency-Key`, order detail, and order history.
- Payments: payment lookup by order and the implemented image-evidence submission workflow.

## Backend boundaries surfaced in the UI

- The order contract accepts a pickup slot, not a delivery address. Saved addresses are displayed on the account page, but are not sent into checkout because the API does not accept them.
- The payments app does not expose a customer-facing gateway initiation, redirect, cancellation, or client-side status-verification endpoint. The order page uses the implemented payment-status and evidence-review endpoints and explains that limitation.
- No backend product seed or contact/social configuration was found. `NEXT_PUBLIC_ENABLE_DEMO_CATALOG=true` enables presentation-only cake cards; demo IDs and prices are never sent to cart/order APIs.

## Development journey checklist

- Browse/search/category/sort: implemented; live verification requires the Django API and catalogue data.
- Product details/customization: implemented against live product and customization endpoints.
- Guest cart and quantity/removal: implemented against live cart endpoints.
- Register/login/cart merge: implemented; tokens remain in memory and are not written to local storage.
- Address reads/account/order history: implemented; address create/edit UI remains absent because checkout does not consume addresses yet.
- Checkout/order creation: implemented with server validation and an idempotency key.
- Payment: implemented only to the extent exposed by the backend; no hosted gateway was invented.

Required environment variables are in `.env.example`.
