# Cart API — Endpoint Specification

**Project:** Leeza Cakes  
**Django app:** `apps.cart`  
**API prefix:** `/api/v1/cart/`  
**Database:** Supabase PostgreSQL  
**Currency:** INR only  
**Fulfilment:** Takeaway only  
**Status:** Approved API contract specification

## 1. Purpose

This document defines the API contract for guest and authenticated shopping carts, cart items, catalogue variants, customization selections, price validation, guest-cart merging, and checkout preparation.

The cart API must follow the finalized decisions in `cart_structure.md`.

The cart manages temporary purchase intent. It does not own product definitions, customization rules, order records, or payment processing.

- `apps.catalog` owns products, variants, and base prices.
- `apps.customization` owns customization definitions and selection validation.
- `apps.cart` owns cart state and cart-item selections.
- `apps.orders` owns order creation and historical snapshots.
- `apps.payments` owns payment processing.

All prices and totals must be calculated and validated on the server.

## 2. API Conventions

### Base path

`/api/v1/cart/`

### Request and response format

Use JSON for normal requests and responses.

Use the project's existing response envelope, exception format, pagination, authentication, and API versioning conventions. Do not create competing conventions inside the cart application.

### Currency

INR is the only supported currency. Serialize monetary values as decimal strings, for example `"1250.00"`.

### Authentication and guest sessions

The API supports:

- Anonymous customers with a valid server-managed session.
- Authenticated customers with one active cart per account.

Guest cart ownership must be established through the configured session mechanism, not by accepting an arbitrary cart ID from the client.

For cookie-based sessions, use the project's configured CSRF protections for unsafe requests. Never expose session credentials in URLs or logs.

### Error responses

Use the existing `apps.common` error format. Examples in this document illustrate semantics, not a requirement to create a second error format.

## 3. Retrieve the Current Cart

### `GET /api/v1/cart/`

**Purpose:** Retrieve the current customer's cart.

**Authentication:** Optional. A valid guest session or authenticated account is required to identify an existing cart.

**Behavior:**

- For an authenticated customer, return their active cart.
- For a guest, return the cart associated with their valid session.
- If no cart exists, return a consistent empty-cart representation or create one according to the chosen persistence strategy.
- Never retrieve another user's cart by accepting an arbitrary cart ID.
- Do not return carts marked converted or otherwise finalized as active carts.

**Success:** `200 OK`

**Example response:**

```json
{
  "id": 42,
  "status": "active",
  "currency": "INR",
  "items": [
    {
      "id": 91,
      "product": {
        "id": 101,
        "name": "Chocolate Truffle Cake",
        "slug": "chocolate-truffle-cake"
      },
      "variant": {
        "id": 501,
        "name": "1 kg"
      },
      "quantity": 1,
      "customizations": [
        {
          "option_id": 11,
          "option_name": "Flavour",
          "choice_id": 102,
          "choice_name": "Red Velvet",
          "text_value": null,
          "price_adjustment": "100.00"
        },
        {
          "option_id": 12,
          "option_name": "Cake Message",
          "choice_id": null,
          "choice_name": null,
          "text_value": "Happy Birthday!",
          "price_adjustment": "0.00"
        }
      ],
      "unit_price": "1200.00",
      "line_subtotal": "1200.00",
      "price_confirmation_required": false
    }
  ],
  "subtotal": "1200.00",
  "price_confirmation_required": false
}
```

All product names, prices, IDs, and customizations in this example are illustrative. Actual response fields must match the implemented models and the catalogue/customization contracts.

The server must calculate `unit_price`, `line_subtotal`, and `subtotal`. They must never be copied from client input.

If an empty cart is returned, use the same schema with an empty `items` array and a subtotal of `"0.00"`.

## 4. Add an Item

### `POST /api/v1/cart/items/`

**Purpose:** Add a product configuration to the current cart.

**Authentication:** Optional, with a valid guest session or authenticated account.

**Request body:**

```json
{
  "product_id": 101,
  "variant_id": 501,
  "quantity": 1,
  "selections": [
    {
      "option_id": 11,
      "choice_ids": [102]
    },
    {
      "option_id": 12,
      "text_value": "Happy Birthday!"
    }
  ]
}
```

`variant_id` may be null only when the catalogue product supports purchase without a variant.

**Required validation:**

1. The product exists and is eligible for purchase.
2. The selected variant belongs to the product and is active.
3. Quantity is a positive integer within configured limits.
4. Each customization option is allowed for the product.
5. Every choice belongs to the correct option and is available for the product.
6. Required options and selection limits are satisfied.
7. Text selections comply with validation rules.
8. All prices are obtained from trusted server-side records.
9. Currency is INR.
10. The requested quantity does not exceed the applicable limits.

**Duplicate-item behavior:**

If the same cart already contains an item with the same product, variant, and normalized customization selections, increment the existing item's quantity.

If any meaningful selection differs, create a separate cart line.

The comparison must use stable IDs and normalized values, not display labels alone.

**Success:** `201 Created` when a new line is created; `200 OK` when an existing line is updated, if this distinction matches project conventions.

Return the updated cart or the affected item consistently.

**Errors:** `400 Bad Request` for invalid input; `404 Not Found` for inaccessible or unavailable products and variants.

## 5. Retrieve a Cart Item

### `GET /api/v1/cart/items/{item_id}/`

**Purpose:** Retrieve an item belonging to the current customer's active cart.

**Authentication:** Optional, with validated guest-session or account ownership.

**Success:** `200 OK`

Return the item, variant, quantity, validated customizations, current calculated prices, and any price-confirmation requirement.

Return `404 Not Found` when the item does not belong to the current cart. Do not reveal whether another customer's item exists.

This endpoint is optional if the frontend can obtain all necessary item details from `GET /api/v1/cart/`.

## 6. Update Item Quantity

### `PATCH /api/v1/cart/items/{item_id}/`

**Purpose:** Update the quantity of an existing cart item.

**Request body:**

```json
{
  "quantity": 2
}
```

**Rules:**

- Accept only supported fields.
- Quantity must be a positive integer within configured limits.
- Validate item ownership.
- Recalculate the line subtotal and cart subtotal.
- Do not trust any submitted price or total.
- Apply concurrency-safe updates where appropriate.

**Success:** `200 OK`

A request that changes only the quantity must not silently modify the selected variant or customization.

## 7. Update Item Customizations

### `PUT /api/v1/cart/items/{item_id}/customizations/`

**Purpose:** Replace the selected customizations for an existing cart item.

**Request body:**

```json
{
  "selections": [
    {
      "option_id": 11,
      "choice_ids": [101]
    },
    {
      "option_id": 12,
      "text_value": "Congratulations!"
    }
  ]
}
```

**Rules:**

- Validate selections through the reusable `apps.customization` service.
- Replace selections atomically; do not leave a partially updated set.
- Recalculate pricing after the change.
- Check whether the updated configuration matches another line in the cart.
- If identical to another line, merge quantities according to the cart-item identity policy.
- Return the resulting cart state.

**Success:** `200 OK`

This endpoint is optional if the project uses a well-defined item update endpoint that supports atomic customization replacement. Do not implement duplicate ways of changing the same state.

## 8. Remove an Item

### `DELETE /api/v1/cart/items/{item_id}/`

**Purpose:** Remove an item from the current cart.

**Authentication:** Optional, with ownership validation.

**Success:** `204 No Content`, or `200 OK` if the project's convention returns the updated cart.

**Rules:**

- Verify that the item belongs to the current cart.
- Recalculate the cart subtotal.
- Do not delete or alter any historical order item.
- Ensure repeated deletion requests are handled consistently.

## 9. Clear the Cart

### `DELETE /api/v1/cart/items/`

**Purpose:** Remove all items from the current active cart.

**Authentication:** Optional, with ownership validation.

**Success:** `204 No Content` or a documented empty-cart response.

Do not delete the cart's historical records if the lifecycle model requires retaining them. This endpoint must not affect converted carts or orders.

This endpoint is optional if the frontend can remove items individually and bulk clearing is not required.

## 10. Validate the Current Cart

### `POST /api/v1/cart/validate/`

**Purpose:** Revalidate products, variants, customizations, quantities, and current prices.

**Authentication:** Optional, with a valid cart session or authenticated account.

**Request body:** No authoritative prices or totals are accepted. The server identifies the cart from the authenticated user or validated session.

**Validation requirements:**

- Products and variants remain purchasable.
- Customization selections remain valid.
- Quantities satisfy limits.
- All monetary values are recalculated.
- Currency remains INR.
- Price changes are detected.
- Unavailable items are identified.
- Invalid items block checkout until resolved.

**Success:** `200 OK` when validation completes, including when the cart requires customer action.

**Example response:**

```json
{
  "valid": true,
  "price_confirmation_required": true,
  "currency": "INR",
  "subtotal": "1350.00",
  "changes": [
    {
      "item_id": 91,
      "previous_unit_price": "1200.00",
      "current_unit_price": "1350.00",
      "reason": "price_changed",
      "requires_confirmation": true
    }
  ],
  "issues": []
}
```

The example demonstrates a price increase. Actual values must be calculated from current server-side data.

If an item is invalid or unavailable, return `valid: false` and structured issues. Use HTTP `200 OK` for a successfully completed validation request with business-level issues, unless the project's established API convention specifies otherwise.

## 11. Confirm Updated Prices

### `POST /api/v1/cart/confirm-prices/`

**Purpose:** Record the customer's acceptance of the currently recalculated cart prices.

**Authentication:** Optional, with validated ownership of the cart.

**Request body:**

```json
{
  "confirmation_token": "server-issued-short-lived-token"
}
```

The token is illustrative. Implement it only if the selected design uses server-issued confirmation tokens.

**Security requirements:**

- The server must determine which prices changed.
- The server must verify that the confirmation applies to the current cart state and price version.
- The server must not trust client-submitted prices, totals, or an unrestricted `confirmed: true` field.
- A token, if used, must be bound to the appropriate cart, price state, and expiry policy.
- If cart contents or prices change after confirmation, invalidate the relevant confirmation and require the necessary customer action again.
- Revalidate the cart before checkout even after confirmation.

**Success:** `200 OK`

Return the updated cart and whether additional confirmation is required.

**Errors:** `400 Bad Request` for invalid or stale confirmation; `409 Conflict` may be used for a stale cart state if consistent with the project's error conventions.

This endpoint is required if explicit price confirmation is part of the checkout flow. It must not be implemented as a generic endpoint that blindly accepts a Boolean flag.

## 12. Merge Guest Cart After Login

### `POST /api/v1/cart/merge/`

**Purpose:** Merge the current guest cart into the authenticated user's active cart after successful authentication.

**Authentication:** Required.

The server must identify the guest cart using the validated pre-login session and the authenticated cart using the logged-in user. Do not accept arbitrary source or destination cart IDs from the client.

**Request body:** No cart IDs or prices are required. The server derives both carts from trusted session and account context.

**Rules:**

1. Validate the guest-session association.
2. Retrieve or create the user's active cart.
3. Revalidate each product, variant, and customization.
4. Merge identical configurations by increasing quantity.
5. Keep different configurations separate.
6. Enforce quantity limits.
7. Recalculate prices.
8. Flag material price changes for customer confirmation.
9. Handle unavailable items explicitly.
10. Persist the merge transactionally and safely handle retries.
11. Clear the guest-cart association only after successful processing.

**Success:** `200 OK`

**Example response:**

```json
{
  "merged": true,
  "cart": {
    "id": 42,
    "currency": "INR",
    "items": [],
    "subtotal": "0.00",
    "price_confirmation_required": false
  },
  "issues": []
}
```

The empty cart is only a response example. A real response must contain the merged cart and any validation issues.

If some items cannot be merged, return a clear result identifying affected items without exposing another user's data. The merge strategy must be documented so clients can recover safely.

## 13. Checkout Preparation

### `POST /api/v1/cart/checkout/validate/`

**Purpose:** Validate that the current cart is ready to be submitted to the order-creation workflow.

**Authentication:** Optional, depending on the chosen guest-checkout and order-creation policies.

**Rules:**

- Revalidate every product and variant.
- Revalidate customization selections.
- Recalculate the subtotal.
- Enforce the INR-only policy.
- Block checkout if prices require confirmation.
- Block checkout if items are invalid or unavailable.
- Do not calculate delivery fees or require a home-delivery address.
- Do not create an order or payment as a side effect of validation.

**Success:** `200 OK`

**Example response:**

```json
{
  "ready_for_checkout": true,
  "currency": "INR",
  "subtotal": "1350.00",
  "price_confirmation_required": false,
  "issues": []
}
```

This endpoint only establishes cart readiness. The orders application must perform its own authoritative validation when creating an order.

If the existing order workflow can perform this validation directly and no frontend preflight is needed, this endpoint may be omitted.

## 14. Cart Conversion and Order Creation

The cart API must not independently create or mark an order as paid.

Order creation belongs to `apps.orders`. The workflow must:

1. Validate the cart and its latest prices.
2. Verify any required customer price confirmation.
3. Create the order and immutable order-item snapshots.
4. Coordinate cart conversion transactionally where possible.
5. Prevent duplicate orders when requests are retried.
6. Ensure a converted cart cannot be used to create a second order unintentionally.

Payment initiation and payment status belong to `apps.payments`.

If order creation requires an authenticated customer, enforce that requirement in the order workflow. Guest carts may still be supported before login.

## 15. Administrative Cleanup

Abandoned carts do not expire automatically.

Manual cleanup may be performed through Django Admin or a separately authorized operational workflow.

Do not expose public endpoints that allow customers to delete arbitrary carts.

Administrative cleanup must:

- Require explicit staff permissions.
- Exclude active checkout operations.
- Preserve historical orders.
- Follow a documented retention policy.
- Avoid deleting carts merely because they are old.

A separate cleanup API endpoint is not required for launch.

## 16. Error Contract

Follow the established `apps.common` error format.

Expected HTTP status codes:

| Status | Meaning |
|---|---|
| `200 OK` | Successful retrieval, update, validation, or merge |
| `201 Created` | New cart item created |
| `204 No Content` | Successful deletion |
| `400 Bad Request` | Invalid quantity, selections, or payload |
| `401 Unauthorized` | Authentication required for the requested operation |
| `403 Forbidden` | Caller lacks permission |
| `404 Not Found` | Item does not exist or does not belong to the current cart |
| `409 Conflict` | Conflicting or stale state, when appropriate |
| `405 Method Not Allowed` | Unsupported HTTP method |
| `429 Too Many Requests` | Rate limit exceeded, if configured |
| `500 Internal Server Error` | Unexpected server failure without sensitive diagnostics |

Never return stack traces, SQL errors, session credentials, storage credentials, or internal filesystem paths.

## 17. Authentication and Permissions Matrix

| Operation | Guest | Authenticated customer | Authorized staff |
|---|---|---|---|
| Retrieve own cart | Allowed | Allowed | According to operational policy |
| Add/update/remove own items | Allowed | Allowed | According to operational policy |
| Validate own cart | Allowed | Allowed | According to operational policy |
| Confirm own price changes | Allowed | Allowed | Not applicable |
| Merge guest cart | Not permitted before login | Allowed for validated guest session | Not applicable |
| Access another user's cart | Denied | Denied | Only through an explicit authorized operational workflow |
| Manual abandoned-cart cleanup | Denied | Denied | Restricted permission |

## 18. OpenAPI Requirements

Document every implemented endpoint using the existing DRF Spectacular configuration.

Include:

- Request and response schemas.
- Authentication and session requirements.
- Ownership rules.
- Quantity limits.
- Variant and customization validation.
- Pricing and confirmation behavior.
- Guest-cart merge behavior.
- Error responses.
- INR monetary serialization.
- Clear separation between cart validation and order creation.

Do not introduce a second API documentation system.

## 19. Testing Requirements

Tests must cover:

1. Guest cart creation and retrieval.
2. Guest-session ownership and isolation.
3. Authenticated cart retrieval and uniqueness.
4. Adding products with and without variants, where allowed.
5. Invalid variant/product relationships.
6. Customization validation.
7. Identical-item merging.
8. Separate lines for different variants or customizations.
9. Quantity limits and invalid quantities.
10. Price recalculation and material price changes.
11. Stale or invalid price confirmation.
12. Guest-cart merge after login.
13. Merge retries and concurrent requests.
14. Unavailable products and choices.
15. INR-only enforcement.
16. Checkout validation without order creation.
17. No delivery-address or delivery-fee requirement.
18. Converted-cart protection and duplicate order prevention.
19. Manual cleanup permissions.
20. OpenAPI schema accuracy.

Use isolated test data. Do not modify production Supabase records.

## 20. Implementation Rules for AI Coding Agents

Before implementation:

1. Read `cart_structure.md`.
2. Inspect existing cart, catalogue, customization, accounts, and orders code.
3. Confirm the configured session and authentication strategy.
4. Inspect shared API response and exception conventions.
5. Review the existing models and migrations.
6. Confirm the order-creation interface and idempotency strategy.

During implementation:

- Do not run migrations against Supabase without explicit approval.
- Do not accept client-submitted prices or totals.
- Do not trust arbitrary cart IDs.
- Do not duplicate customization validation.
- Do not implement coupons or delivery functionality at launch.
- Do not automatically expire abandoned carts.
- Do not create redundant endpoints when an existing endpoint satisfies the contract.
- Do not modify production data or deploy without explicit approval.

After implementation:

- Run Ruff and Django checks.
- Run relevant tests and the full test suite.
- Check migration consistency without applying migrations.
- Validate the OpenAPI schema.
- Review the final diff and report verified results accurately.

## 21. Definition of Done

The cart API is complete when:

- Guest and authenticated carts work securely.
- Each authenticated customer has at most one active cart.
- Guest carts merge safely after login.
- Identical configurations merge deterministically.
- Cake sizes use catalogue variants.
- Customizations use normalized related records.
- Prices are recalculated server-side.
- Material price changes require explicit customer confirmation.
- INR is the only supported currency.
- Checkout is takeaway-only.
- Abandoned carts have no automatic expiry.
- Administrative cleanup is appropriately restricted.
- Orders receive independent immutable snapshots.
- Tests, Ruff, Django checks, and OpenAPI validation pass.
- No unapproved production changes or migrations have occurred.

**Final requirement:** Implement only the endpoints needed by the actual frontend and checkout workflow. Optional endpoints in this document must not become duplicate functionality. Any deviation from this contract must be documented in both `cart_api.md` and `cart_structure.md`.