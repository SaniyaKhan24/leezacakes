# Cart App — Architecture and Structure

**Project:** Leeza Cakes  
**Django app:** `apps.cart`  
**Purpose:** Define the architecture, data model, business rules, and integration boundaries for managing customer shopping carts.

## 1. Purpose

The `cart` application manages a customer's active shopping cart before checkout. It supports adding products, selecting quantities and variants, storing validated cake customizations, updating or removing items, and calculating the current cart subtotal.

The cart is a temporary purchasing workflow, not an order record. The `orders` application owns order creation and order history, while `payments` owns payment processing.

The cart must always use server-side catalogue and customization data to validate items and calculate prices. Frontend-supplied prices, discounts, and totals are never authoritative.

## 2. Scope and Responsibilities

### In scope

- Creating or retrieving the current cart.
- Supporting authenticated customers and, if required, anonymous sessions.
- Adding catalogue products to a cart.
- Selecting product variants, such as cake sizes.
- Storing validated customization selections.
- Updating item quantities.
- Removing cart items.
- Calculating item prices and cart subtotal.
- Revalidating product availability and pricing.
- Handling expired, inactive, or unavailable products.
- Associating a guest cart with an account after login, if guest carts are supported.
- Providing a normalized cart representation for the frontend.
- Preparing validated cart data for checkout.

### Out of scope

| Responsibility | Owning application |
|---|---|
| Product catalogue, variants, and base prices | `apps.catalog` |
| Customization options and selection validation | `apps.customization` |
| Customer accounts and authentication | `apps.accounts` |
| Order creation, order items, and order history | `apps.orders` |
| Payment sessions, transactions, refunds, and payment status | `apps.payments` |
| Delivery fee and delivery eligibility, if separately modeled | The explicitly designated delivery/pricing component |
| Coupons and promotional rules, if implemented as a separate domain | The designated promotions component |
| Email, SMS, and order notifications | `apps.notifications` |
| Shared exceptions, pagination, and response conventions | `apps.common` |

Do not implement a second product model, order model, payment system, or customization engine inside the cart application.

## 3. Architectural Principles

1. **Server-authoritative pricing:** Derive every item price from trusted catalogue and customization records.
2. **Temporary state:** A cart represents current purchase intent, not a completed transaction.
3. **Ownership enforcement:** Customers must only access carts they own or an explicitly authorized guest cart.
4. **Explicit item identity:** Define when two selections represent the same cart item.
5. **Revalidation:** Prices and availability may change between adding an item and checkout.
6. **Transactional writes:** Protect quantity updates, item creation, and checkout handoff from inconsistent concurrent operations.
7. **Historical separation:** Orders must preserve their own snapshots and must not depend on a mutable cart.
8. **No client-side trust:** Ignore or reject submitted prices, totals, and payment status.
9. **Consistent API behavior:** Use shared authentication, pagination, error handling, and response conventions.
10. **Minimal persistence:** Store only the cart state needed to resume and validate the purchase workflow.

## 4. Recommended Data Model

Inspect the existing repository before implementation. Reuse equivalent models if they already exist.

### 4.1 `Cart`

Represents a customer's active cart.

Suggested fields:

| Field | Type | Purpose |
|---|---|---|
| `id` | Primary key | Internal identifier |
| `user` | ForeignKey to user, nullable only if guest carts are supported | Authenticated owner |
| `session_key` | Nullable identifier, if guest carts are supported | Guest-cart association |
| `status` | Choice field | Active, converted, abandoned, or expired as required |
| `currency` | CharField | Currency used for cart pricing |
| `created_at` | DateTimeField | Creation timestamp |
| `updated_at` | DateTimeField | Last update timestamp |
| `expires_at` | Nullable DateTimeField | Expiration time, if required |

Rules:

- Define whether the system permits one active cart per user or multiple carts.
- Enforce the chosen ownership and uniqueness rules in the database where practical.
- Do not store a mutable `total` field unless there is a clear need for caching and a reliable invalidation strategy.
- If a cached total is introduced, never treat it as the source of truth during checkout.
- A converted cart must not silently become an editable active cart again.

**Recommendation:** Start with one active cart per authenticated user. Add guest carts only if the storefront requires checkout preparation before login.

### 4.2 `CartItem`

Represents one selected product configuration and quantity.

Suggested fields:

| Field | Type | Purpose |
|---|---|---|
| `id` | Primary key | Internal identifier |
| `cart` | ForeignKey | Parent cart |
| `product` | ForeignKey to catalogue product | Selected product |
| `variant` | Nullable ForeignKey to catalogue variant, if variants exist | Selected size or other variant |
| `quantity` | PositiveIntegerField | Number of units |
| `created_at` | DateTimeField | Creation timestamp |
| `updated_at` | DateTimeField | Last update timestamp |

Additional fields should be introduced only if required by the pricing and workflow design.

A cart item must not rely exclusively on a product name, price, or other frontend-provided snapshot to identify its current catalogue product.

#### Cart item identity

Define a deterministic rule for whether an add-item request creates a new line or increments an existing one.

A reasonable default is:

- Same cart.
- Same product.
- Same variant.
- Same normalized customization selections.

If all are equivalent, the system may increment the existing item's quantity. If customization differs, create a separate line item.

Do not merge items with different inscriptions, flavours, sizes, or other meaningful selections.

### 4.3 `CartItemCustomization`

Use a normalized child model if cart customizations require structured querying or reliable persistence.

Suggested fields:

| Field | Type | Purpose |
|---|---|---|
| `id` | Primary key | Internal identifier |
| `cart_item` | ForeignKey | Parent cart item |
| `option` | ForeignKey or stable reference | Selected customization option |
| `choice` | Nullable ForeignKey or stable reference | Selected predefined choice |
| `text_value` | Nullable text field | Customer-entered value for text options |
| `created_at` | DateTimeField | Creation timestamp |

The exact relationship depends on the existing `apps.customization` models.

Validation rules:

- Each selection belongs to the correct cart item.
- The selected option is valid for the selected product.
- The choice belongs to that option and is eligible for the product.
- Text values are accepted only for text-based options.
- Invalid combinations cannot be persisted.

If customizations require a flexible but small payload, a JSON representation may be considered. However, use a documented schema, strict validation, and deliberate snapshot behavior. Do not use unrestricted JSON as a substitute for domain modeling.

### 4.4 Customization price snapshots

A cart may store calculated pricing snapshots for display or performance, but those values are temporary and must be revalidated.

If stored, snapshot fields must have a clear purpose, such as:

- Last validated unit price.
- Last validated customization adjustment.
- Currency.
- Last price-validation timestamp.

Do not let snapshots become authoritative when catalogue prices change.

At checkout, recalculate all applicable prices from trusted server-side data and pass validated data to the order-creation workflow.

## 5. Pricing Model

The cart must distinguish between:

- Product or variant base price.
- Customization adjustments.
- Quantity.
- Any explicitly supported discounts.
- Delivery charges and taxes, if applicable.

A basic calculation, when all customization adjustments are additive, is:

`line subtotal = (base unit price + customization adjustments per unit) × quantity`

`cart subtotal = sum(line subtotals)`

These formulas are illustrative. The final implementation must follow the agreed pricing policy and must not double-count variant pricing, discounts, taxes, or other charges.

### Pricing requirements

- Use `Decimal` arithmetic and Django `DecimalField` for monetary values.
- Use a single, explicitly defined currency policy.
- Calculate prices on the server.
- Validate quantity bounds.
- Revalidate current product and variant prices.
- Revalidate customization eligibility and adjustments.
- Reject or flag unavailable products.
- Return a clear indication when the cart needs customer confirmation after a material price or availability change.
- Never trust frontend-submitted subtotal, discount, tax, or total fields.

The cart subtotal is not necessarily the final checkout amount. The order/pricing workflow must determine the final payable amount using the project's defined rules.

## 6. Cart Lifecycle

Recommended lifecycle:

1. A customer opens the storefront.
2. The system retrieves or creates the customer's active cart.
3. The customer adds a product, variant, quantity, and optional customizations.
4. The server validates the product and all selections.
5. The cart stores the item and returns the current cart representation.
6. The customer updates quantities, removes items, or changes customizations.
7. The cart recalculates applicable prices.
8. Before checkout, the server revalidates all items and pricing.
9. The order workflow creates an order with independent snapshots.
10. The cart is marked converted or otherwise finalized according to the agreed workflow.

Do not create an order merely by retrieving the cart. Order creation must be an explicit, validated workflow.

## 7. Guest and Authenticated Cart Strategy

Choose one strategy before implementing the model.

### Option A — Authenticated carts only

- Every cart belongs to an authenticated user.
- The API requires authentication for all cart operations.
- A user can access only their own active cart.
- The frontend prompts the customer to log in before using persistent cart features.

This is the simpler initial implementation.

### Option B — Guest carts

- Anonymous carts are associated with a secure session or another explicitly designed guest-cart identifier.
- The server must not accept arbitrary cart IDs as proof of ownership.
- Session credentials must not be exposed in logs or analytics.
- Cart merging after login must validate every product, variant, and customization.
- Duplicate lines must follow the same cart-item identity rule.
- Expiration and cleanup must be defined.
- Guest carts must not expose another customer's data.

Do not implement both strategies implicitly. Select the required behavior and document it before creating migrations.

## 8. Application Structure

Use this structure where it fits the existing repository:

```text
apps/
└── cart/
    ├── __init__.py
    ├── admin.py
    ├── apps.py
    ├── models.py
    ├── serializers.py
    ├── selectors.py
    ├── services/
    │   ├── __init__.py
    │   ├── cart_service.py
    │   └── pricing.py
    ├── permissions.py
    ├── urls.py
    ├── views.py
    ├── exceptions.py
    ├── tests/
    │   ├── __init__.py
    │   ├── test_models.py
    │   ├── test_services.py
    │   ├── test_pricing.py
    │   ├── test_api.py
    │   └── test_permissions.py
    └── migrations/
        └── __init__.py
```

Structure rules:

- `models.py` defines persistence and database-level invariants.
- `serializers.py` validates HTTP request payloads and represents responses.
- `selectors.py` contains reusable read queries when needed.
- `services/cart_service.py` coordinates add, update, remove, and validation operations.
- `services/pricing.py` calculates server-authoritative cart pricing.
- `views.py` remains thin and delegates domain operations to services.
- `permissions.py` enforces ownership and administrative access.
- Do not create empty modules merely to match this layout.
- Keep pricing rules centralized rather than duplicating them across endpoints.

## 9. Integration Boundaries

### Catalog

The cart references products and variants from `apps.catalog`.

Before an item is accepted or checked out, verify that the selected product and variant are valid and purchasable under catalogue rules.

Do not copy the catalogue's product-management responsibilities into the cart.

### Customization

The cart calls the reusable validation service from `apps.customization`.

The cart stores the validated selections associated with each item. It must not independently reimplement option eligibility or choice-pricing rules.

Selections must be revalidated when necessary, especially before checkout.

### Accounts

The cart uses the configured authentication identity and enforces ownership. It must not duplicate account profiles or password logic.

### Orders

The cart hands validated purchase data to the order-creation workflow.

The orders application must create independent order and order-item snapshots. Once the order is created, subsequent cart edits must not modify that order.

Cart conversion and order creation should be coordinated to prevent duplicate orders or inconsistent state if requests are retried.

### Payments

The cart must not initiate payment processing directly or maintain payment status. The checkout/order workflow coordinates order creation and payment initiation.

### Common

Use shared error handling, pagination, response conventions, and other common infrastructure from `apps.common`.

## 10. Transactional Integrity and Concurrency

Cart operations must be safe under concurrent requests.

- Use database transactions for multi-record changes.
- Consider `select_for_update()` where appropriate and supported by the production database.
- Prevent duplicate active carts when the selected strategy requires uniqueness.
- Ensure quantity updates do not overwrite concurrent changes unexpectedly.
- Validate all submitted item IDs against the current user's cart.
- Make checkout and order creation idempotent where required.
- Do not assume a client request will be sent only once.
- Recalculate prices inside the relevant checkout transaction or under a documented consistency strategy.

Supabase PostgreSQL is the project's database, so database constraints and transaction behavior must be tested against the supported PostgreSQL configuration.

## 11. Security and Data Integrity

- Enforce cart ownership on every read and write.
- Never authorize a request merely because the caller knows a cart or item ID.
- Reject invalid product, variant, and customization combinations.
- Reject non-positive quantities and quantities above configured limits.
- Do not accept client-supplied authoritative prices or totals.
- Do not expose another customer's cart or private customization text.
- Prevent inactive products or variants from being newly purchased.
- Preserve historical order data when catalogue or customization records change.
- Avoid hard-deleting referenced records without a defined deletion policy.
- Use database constraints for important invariants.
- Avoid logging private inscriptions, session identifiers, or sensitive customer data unnecessarily.
- Use the project's configured authentication, CSRF, and rate-limiting controls as applicable.

## 12. Testing Strategy

### Model tests

- Cart ownership and status.
- Cart-item quantity constraints.
- Variant/product relationship validation.
- Customization selection relationships.
- Active-cart uniqueness, if required.
- Database constraints and deletion behavior.

### Service tests

- Create or retrieve a cart.
- Add a valid product.
- Increment a matching line item.
- Create a separate line for different customizations.
- Update quantity.
- Remove an item.
- Reject invalid product/variant combinations.
- Reject invalid customization selections.
- Handle inactive or unavailable catalogue items.
- Recalculate prices after a catalogue price change.

### Pricing tests

- Correct base-price calculation.
- Correct customization adjustment calculation.
- Quantity multiplication.
- Decimal precision.
- Currency consistency.
- No double-counting of size or variant pricing.
- Tampered frontend prices are ignored or rejected.
- Discounts, taxes, and delivery fees follow their documented ownership and rules.

### API and permission tests

- Users cannot access another user's cart.
- Invalid item IDs do not bypass ownership checks.
- Malformed quantities return consistent errors.
- Pagination and response schemas follow project conventions.
- Authentication requirements match the chosen guest-cart strategy.
- All implemented endpoints appear in OpenAPI.

### Workflow tests

- Checkout revalidates all cart items.
- Price changes are handled according to the documented policy.
- Duplicate checkout requests do not create duplicate orders.
- Order snapshots remain independent of subsequent cart changes.
- Concurrent updates do not corrupt cart state.

Tests must use isolated test data and must not modify production Supabase records.

## 13. Implementation Order

1. Inspect existing catalogue, customization, accounts, and orders models.
2. Decide whether guest carts are required.
3. Finalize cart identity and item-merging behavior.
4. Finalize pricing and currency rules.
5. Implement cart and cart-item persistence.
6. Implement customization-selection persistence if required.
7. Implement cart services and centralized pricing.
8. Implement API serializers, views, permissions, and routes.
9. Integrate with catalogue and customization validation.
10. Implement checkout handoff to orders.
11. Add concurrency, ownership, pricing, and integration tests.
12. Validate OpenAPI, migration consistency, Ruff, Django checks, and the full test suite.

Do not implement order or payment processing inside the cart application.

## 14. 
## 1. Guest Carts

**Decision: Supported.**

Customers may add products to their cart without logging in.

- Associate guest carts with a secure server-managed session.
- Never treat a client-submitted cart ID as proof of ownership.
- Allow guests to view, update, and remove items only from their own cart.
- Do not expose guest cart data to other customers.
- Preserve the cart across requests using the configured session strategy.

### Guest cart merge

When a guest logs in:

1. Retrieve the guest's cart using the validated session.
2. Retrieve or create the authenticated user's active cart.
3. Revalidate every product, variant, and customization.
4. Merge identical configurations by increasing quantity.
5. Keep different configurations as separate cart items.
6. Apply quantity limits and current availability rules.
7. Recalculate current prices.
8. Handle price changes according to the customer-confirmation policy.
9. Persist the merge transactionally.
10. Invalidate or clear the guest cart association after successful merging.

Do not discard the guest cart if the merge fails. The operation must be recoverable and must not create duplicate items on retries.

## 2. Active Cart Policy

**Decision: One active cart per authenticated user.**

- Enforce one active cart per authenticated user.
- Use database constraints where practical to protect this invariant against concurrent requests.
- A guest cart is identified separately through its validated session.
- Define explicit cart states, such as `active` and `converted`, according to the implemented lifecycle.
- A converted cart must not silently become editable again.
- Do not create multiple active carts for the same authenticated user through concurrent requests.

Abandoned carts must not expire automatically. Manual administrative cleanup is permitted.

## 3. Cart Item Identity and Merging

**Decision: Merge identical configurations by increasing quantity.**

Two cart items are considered identical only when all of the following match:

- Cart ownership.
- Catalogue product.
- Selected catalogue variant.
- Normalized customization selections.

Customization comparisons must use stable identifiers and normalized values, not display labels alone.

For text-based customizations, compare normalized text according to the documented text-normalization policy. Do not change the customer's intended message through aggressive normalization.

### Expected behavior

- Same product, variant, and customization selections: increase the existing item's quantity.
- Same product but different variant: create a separate line.
- Same product and variant but different flavour or decoration: create a separate line.
- Same product and variant but different cake message: create a separate line.
- Invalid or unavailable selections: reject the operation.

Recalculate the line subtotal after quantity changes. Enforce server-side quantity limits.

## 4. Product Variants and Cake Sizes

**Decision: Cake sizes are catalogue variants.**

`apps.catalog` owns product variants and their prices.

Examples include:

- 500 g
- 1 kg
- 2 kg

These are illustrative examples; actual variants depend on the product configuration.

The cart must reference the selected catalogue variant when one exists. It must not create a second size-pricing system in `apps.customization`.

Validate that:

- The variant belongs to the selected product.
- The variant is active and purchasable.
- The variant's price is obtained from trusted catalogue data.
- Variant pricing is not counted twice as a customization adjustment.

If a product does not require variants, the cart may store a null variant reference, subject to the catalogue model and product rules.

## 5. Customization Storage

**Decision: Use normalized related database records.**

Store each structured customization selection as a related record associated with its cart item.

A selection may reference:

- A customization option.
- A predefined choice, where applicable.
- A customer-entered text value, for text-based options.

Use the models and relationships defined in `customization_structure.md`.

The cart must not duplicate customization option definitions or pricing rules.

### Validation

- Validate every selection through the reusable service in `apps.customization`.
- Confirm the option and choice are eligible for the selected product.
- Reject invalid, duplicate, inactive, or unsupported selections.
- Enforce required-option and selection-count constraints.
- Derive price adjustments from trusted server-side records.
- Preserve a normalized representation for reliable comparison and merging.

When an order is created, copy the relevant selection names, values, and prices into immutable order-item snapshots owned by `apps.orders`.

## 6. Price Changes and Customer Confirmation

**Decision: Recalculate prices and require customer confirmation when prices materially change.**

The cart's displayed prices are provisional until revalidated.

### Required behavior

1. Recalculate the current product or variant price and customization adjustments at appropriate validation points.
2. Compare the newly calculated amount with the previously acknowledged cart amount.
3. If a material price change occurs, flag the affected item or cart as requiring confirmation.
4. Return the updated prices and a clear explanation of the change.
5. Do not allow checkout to proceed using the old acknowledged price.
6. Require an explicit customer action to accept the updated amount.
7. Revalidate again before creating the order.
8. Persist the newly acknowledged price state so repeated requests do not continually trigger the same confirmation.

The implementation must define what constitutes a material price change. At minimum, any increase in the payable amount caused by a catalogue or customization price change must require confirmation. Other changes should follow a documented policy.

Do not silently increase the customer's expected payment amount.

If an item becomes unavailable or its customization is no longer valid, require the customer to resolve the issue before checkout.

**Important:** Client-submitted totals and confirmation flags are never authoritative. The server must determine the current price, verify the required confirmation, and validate the checkout state.

## 7. Currency and Pricing

**Decision: INR only.**

- Use `INR` as the supported currency.
- Store monetary values using `DecimalField`.
- Use Python `Decimal` for calculations.
- Serialize monetary amounts as decimal strings.
- Do not introduce currency conversion or multi-currency infrastructure at launch.
- Validate all prices and adjustments against server-side catalogue and customization records.

The basic calculation, subject to the agreed pricing rules, is:

`Line subtotal = (variant/base price + per-unit customization adjustments) × quantity`

`Cart subtotal = sum of valid line subtotals`

Do not double-count variant pricing, discounts, taxes, or other charges.

The cart subtotal represents the current merchandise amount. It is not an independent payment amount or a completed order total.

## 8. Promotions and Discounts

**Decision: No promotions at launch; preserve a future extension point.**

The initial cart implementation must not include coupon redemption, discount stacking, promotional campaigns, or a full promotions engine.

However:

- Keep pricing calculations sufficiently modular to support future discounts.
- Do not hardcode assumptions that make future promotions impossible.
- Do not add unused models or endpoints in anticipation of future features.
- Implement promotions later as a documented feature with explicit ownership and pricing rules.

## 9. Delivery, Pickup, and Taxes

**Decision: Takeaway only. No home delivery.**

The launch workflow supports customers collecting their orders.

Therefore, the cart does not need to implement:

- Home-delivery addresses.
- Delivery fees.
- Delivery-zone eligibility.
- Shipping methods.
- Courier integrations.
- Delivery estimates.

Do not add delivery-specific cart fields or APIs unless the business requirements change.

Pickup scheduling, collection time slots, and applicable tax calculations must be implemented only if required by the agreed order workflow. Do not assume that they are automatically part of the cart.

The order workflow remains responsible for validating the final order and applicable charges.

## 10. Cart Expiry and Cleanup

**Decision: No automatic expiry; allow manual administrative cleanup.**

- Do not automatically expire or delete abandoned carts.
- Do not require an `expires_at` field unless a future requirement justifies it.
- Allow authorized administrators to inspect and clean up abandoned carts.
- Define the administrative cleanup policy before implementing destructive cleanup operations.
- Never delete or modify historical orders as part of cart cleanup.
- Preserve auditability where required by the project's operational policies.

A manual cleanup operation must be restricted to authorized staff and must not delete active carts or carts associated with an in-progress checkout.

## 11. Checkout and Order Conversion

The cart application validates and prepares purchase data. The orders application owns order creation and historical order records.

Before checkout:

- Validate product and variant availability.
- Revalidate customization selections.
- Recalculate all applicable prices.
- Check whether customer confirmation is required.
- Validate quantities and currency.
- Reject invalid or unavailable items.
- Ensure the request cannot create duplicate orders when retried.

On successful order creation, preserve independent order-item snapshots. Mark or convert the cart according to the agreed lifecycle.

Do not treat cart conversion as payment success. Payment processing belongs to `apps.payments`.

## 12. Implementation Structure

Recommended structure:

```text
apps/cart/
├── models.py
├── serializers.py
├── selectors.py
├── services/
│   ├── __init__.py
│   ├── cart_service.py
│   ├── pricing.py
│   └── merge.py
├── permissions.py
├── urls.py
├── views.py
├── exceptions.py
├── admin.py
├── apps.py
├── tests/
│   ├── test_models.py
│   ├── test_services.py
│   ├── test_pricing.py
│   ├── test_merge.py
│   ├── test_api.py
│   └── test_permissions.py
└── migrations/
```

Create only the modules needed by the implementation. Keep pricing, merging, and cart operations in reusable service functions rather than duplicating business logic across API views.

## 13. Required Tests

Tests must verify:

1. Guest carts work without authentication.
2. Guest carts cannot be accessed by unrelated sessions.
3. Each authenticated user has at most one active cart.
4. Guest cart merging works after login.
5. Merge retries do not duplicate quantities.
6. Identical configurations merge correctly.
7. Different variants or customizations remain separate.
8. Cake sizes use catalogue variants.
9. Customizations are stored as normalized related records.
10. Price changes trigger customer confirmation.
11. Checkout cannot proceed with an unconfirmed material price change.
12. Prices are recalculated from trusted records.
13. Currency is restricted to INR.
14. Invalid or unavailable selections block checkout.
15. No automatic cart expiry occurs.
16. Administrative cleanup is appropriately restricted.
17. Takeaway-only checkout does not introduce delivery charges or delivery-address requirements.
18. Order snapshots remain unchanged when cart or catalogue data changes.
19. Concurrent requests do not violate cart uniqueness or corrupt quantities.
20. Repeated checkout requests do not create duplicate orders.

## 14. Migration and Production Safety

These decisions define the architecture only.

- Do not run migrations as part of documenting or approving these decisions.
- Do not modify production Supabase data.
- Inspect existing models and migrations before implementing schema changes.
- Do not change existing database records merely to conform to a new proposed model.
- Review migration plans before any database operation.
- Obtain explicit approval before applying migrations to Supabase or deploying changes.

## 15. Final Decision Summary

| Area | Approved decision |
|---|---|
| Guest carts | Supported |
| Guest identification | Secure server-managed session |
| Authenticated carts | One active cart per user |
| Guest login | Merge into the authenticated cart with full revalidation |
| Identical items | Merge by increasing quantity |
| Different configurations | Separate cart lines |
| Cake sizes | Catalogue variants |
| Customization storage | Normalized related records |
| Price changes | Recalculate and require confirmation for material changes |
| Currency | INR only |
| Promotions | Excluded at launch; future-compatible design |
| Fulfilment | Takeaway only |
| Automatic cart expiry | Disabled |
| Manual cleanup | Permitted for authorized administrators |
| Production migrations | Not authorized by these decisions |

**Implementation acceptance criterion:** `cart_structure.md`, `cart_api.md`, and the eventual implementation must use these decisions consistently. Any proposed deviation must be documented and approved before implementation.

## 15. Definition of Done

The cart foundation is complete when:

- Cart ownership and lifecycle are explicit.
- Item identity and merge behavior are deterministic.
- Products, variants, and customizations are validated server-side.
- Pricing is calculated consistently using decimal arithmetic.
- Invalid or unavailable items are handled safely.
- Cart operations enforce ownership and quantity constraints.
- Checkout revalidates pricing and availability.
- Order creation produces independent historical snapshots.
- Concurrency and duplicate-request risks are addressed.
- Tests, Ruff, and Django checks pass.
- OpenAPI documentation matches the implemented API.
- No production database changes, deployments, or unrelated application changes occur without explicit approval.