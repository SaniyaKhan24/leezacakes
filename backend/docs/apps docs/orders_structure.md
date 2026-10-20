# Orders App — Architecture and Structure

**Project:** Leeza Cakes  
**Path:** `backend/docs/apps/orders_structure.md`  
**App:** `apps.orders`  
**API prefix:** `/api/v1/orders/`  
**Status:** Architecture specification  
**Currency:** INR only  
**Fulfilment:** Takeaway / customer pickup only

---

## 1. Purpose and Scope

The `orders` app owns the order lifecycle for Leeza Cakes, from creating an order from a validated cart through payment verification, preparation, pickup readiness and completion.

It converts a customer's cart into a durable order record. Once created, an order must retain the product details, selected variants, customization choices, quantities and prices that were agreed upon at checkout, even if the original catalogue or customization configuration changes later.

The app is responsible for:

- Creating orders from authenticated customers' carts.
- Validating checkout data and the current state of the cart.
- Capturing mandatory customer contact information.
- Recording the selected pickup slot.
- Creating immutable order-item and customization snapshots.
- Tracking order status and its permitted transitions.
- Exposing customer order history and order details.
- Providing authorized staff with order-management operations.
- Maintaining an order-status history.
- Coordinating with the `payments` app for UPI payment verification outcomes.
- Preventing duplicate orders and inconsistent state changes.
- Preserving historical orders without automatic deletion.

The app does **not** own payment transactions, product catalogue management, cart management, customization definitions, notification delivery or authentication.

## 2. Confirmed Business Rules

These rules are requirements, not optional implementation suggestions.

1. Customers must log in before placing an order. Guest customers may use a cart, but cannot create an order.
2. A customer must provide a phone number. Email is optional.
3. Leeza Cakes displays its UPI QR code for payment. UPI QR payment is the only supported launch payment method.
4. Cash on pickup is not allowed.
5. Customers must upload a payment screenshot for manual staff verification.
6. An order starts in a state indicating that payment is awaiting staff verification.
7. Order status and payment status must be tracked independently.
8. Customers cannot cancel submitted orders through the customer-facing application.
9. Customers select their pickup slot during checkout, before submitting the order.
10. Pickup slots should start approximately 30–45 minutes after ordering, subject to the final lead-time and slot-availability policy.
11. Orders are for pickup only. Home delivery, delivery addresses and delivery fees are out of scope for launch.
12. INR is the only supported currency.
13. Promotions, coupons and discount campaigns are out of scope for launch.
14. Tax calculation and tax presentation must remain unconfigured until the business defines the policy.
15. Historical orders must not be automatically deleted.
16. Order creation must be transactional and idempotent.
17. The server is authoritative for cart contents, product eligibility, customization validity and all monetary values.
18. Order items and customization details must be snapshotted at order creation.
19. Payment processing and payment verification records belong to `apps.payments`.
20. Database migrations and production-data changes must not be run without explicit approval.

## 3. App Responsibilities and Boundaries

### 3.1 What orders owns

- Order creation and persistence.
- Order numbers and customer ownership.
- Order lifecycle and permitted state transitions.
- Customer contact snapshots.
- Pickup-slot selection snapshots.
- Order-item snapshots.
- Customization snapshots.
- Order totals derived from validated server-side data.
- Order-status history.
- Customer order history and detail access.
- Authorized staff order-management operations.
- Checkout idempotency and transactional consistency.

### 3.2 What other apps own

| App | Responsibility |
|---|---|
| `accounts` | Authentication, user identity, profiles and saved addresses |
| `cart` | Active customer cart, guest cart, cart items, quantities and cart merging |
| `catalog` | Products, categories, variants, current catalogue prices and publication state |
| `customization` | Customization definitions, allowed choices and validation rules |
| `payments` | UPI payment records, screenshot evidence, manual verification and payment status |
| `notifications` | Email, SMS or other notification delivery |
| `common` | Shared exceptions, validators, permissions utilities where appropriate, pagination and common infrastructure |

Orders may call the relevant app's service layer but must not duplicate its business logic.

The `orders` app must not implement its own UPI payment processor or treat a customer-uploaded screenshot as proof that payment succeeded.

## 4. Recommended Directory Structure

Use a modular structure with explicit separation between models, serializers, views, services and status-transition logic.

```text
backend/
└── apps/
    └── orders/
        ├── __init__.py
        ├── apps.py
        ├── admin.py
        ├── models/
        │   ├── __init__.py
        │   ├── order.py
        │   ├── order_item.py
        │   ├── order_item_customization.py
        │   └── order_status_history.py
        ├── serializers/
        │   ├── __init__.py
        │   ├── checkout.py
        │   ├── order.py
        │   ├── order_item.py
        │   └── staff.py
        ├── views/
        │   ├── __init__.py
        │   ├── checkout.py
        │   ├── customer.py
        │   └── staff.py
        ├── services/
        │   ├── __init__.py
        │   ├── checkout.py
        │   ├── order_number.py
        │   ├── snapshots.py
        │   ├── status_transitions.py
        │   └── totals.py
        ├── selectors/
        │   ├── __init__.py
        │   ├── customer_orders.py
        │   └── staff_orders.py
        ├── permissions.py
        ├── exceptions.py
        ├── urls.py
        ├── tests/
        │   ├── __init__.py
        │   ├── test_checkout.py
        │   ├── test_order_models.py
        │   ├── test_order_permissions.py
        │   ├── test_order_snapshots.py
        │   ├── test_order_transitions.py
        │   ├── test_order_totals.py
        │   ├── test_order_idempotency.py
        │   └── test_staff_orders.py
        └── migrations/
            └── __init__.py
```

This is the target structure, not confirmation that all these files already exist. The implementation should follow the existing repository conventions where they differ, without introducing duplicate modules or redundant abstractions.

## 5. Data Model

### 5.1 Order

**Module:** `apps/orders/models/order.py`

The `Order` model represents the complete customer order and its current lifecycle state.

Recommended fields:

| Field | Suggested type | Purpose |
|---|---|---|
| `id` | UUID primary key | Stable internal identifier |
| `order_number` | Unique string | Customer-facing order reference |
| `user` | Foreign key to configured user model | Customer who placed the order |
| `status` | Choice field | Current order lifecycle state |
| `payment_status` | Choice field or read-only derived representation | Current payment state as synchronized from the payments domain |
| `customer_name` | String | Name captured at checkout |
| `customer_phone` | String | Mandatory phone number snapshot |
| `customer_email` | Nullable string | Optional email snapshot |
| `pickup_slot_start` | DateTime | Selected pickup-slot start |
| `pickup_slot_end` | DateTime | Selected pickup-slot end |
| `currency` | Fixed-value choice | `INR` |
| `subtotal` | Decimal | Sum of validated item amounts |
| `discount_total` | Decimal | Zero at launch; future-compatible only if needed |
| `tax_total` | Nullable Decimal | Unconfigured until the tax policy is decided |
| `grand_total` | Decimal | Amount payable under the configured pricing policy |
| `customer_note` | Nullable text | Optional customer instructions, if enabled |
| `idempotency_key` | String or equivalent scoped key | Prevents duplicate checkout submissions |
| `created_at` | DateTime | Order creation time |
| `updated_at` | DateTime | Last update |
| `confirmed_at` | Nullable DateTime | Time the order is confirmed after the required checks |
| `completed_at` | Nullable DateTime | Time the order is completed |
| `cancelled_at` | Nullable DateTime | Administrative/system cancellation timestamp, if cancellation is supported internally |

Implementation notes:

- Use the project's configured user model, not a hard-coded Django user class.
- The `user` relationship is mandatory because guest checkout is not allowed.
- Preserve the customer's contact details as they were at checkout. Later profile edits must not silently rewrite historical orders.
- `order_number` must be unique, generated server-side and safe to expose publicly.
- Use `DecimalField` for monetary values. Never use floating-point arithmetic for prices.
- Keep the currency fixed to INR for launch and validate it server-side.
- Do not allow customers to submit `status`, `payment_status`, `grand_total` or other authoritative fields directly.
- Do not calculate `payment_status` from `status`; the two represent different concepts.
- `tax_total` must not silently become zero merely because tax configuration is missing. The checkout service must follow an explicitly configured pricing policy or fail safely until one is established.
- Only add fields such as delivery details, coupon codes or shipping charges if the business scope changes.

The exact field names may be adapted to the existing codebase, but their responsibilities and invariants must remain intact.

### 5.2 OrderItem

**Module:** `apps/orders/models/order_item.py`

Each `OrderItem` records one purchased product configuration.

Recommended fields:

| Field | Purpose |
|---|---|
| `id` | Stable identifier |
| `order` | Parent order foreign key |
| `product` | Nullable reference to the original catalogue product, if retained |
| `variant` | Nullable reference to the original catalogue variant, if retained |
| `product_name_snapshot` | Product name at checkout |
| `variant_name_snapshot` | Selected size/variant label at checkout |
| `sku_snapshot` | Optional product/variant code snapshot |
| `quantity` | Ordered quantity |
| `unit_base_price` | Base unit price captured at checkout |
| `unit_customization_total` | Customization price per unit |
| `unit_price` | Final unit price under the configured pricing rules |
| `line_total` | Final total for the line |
| `created_at` | Creation timestamp |

Requirements:

- Cake sizes are catalogue variants, not free-form order fields.
- Every line must reference a valid product and variant at the time the order is created, where the catalogue model requires a variant.
- Persist readable product and variant snapshots even if the live catalogue objects are later archived or removed.
- Historical order display must not depend on fetching the current product name or price.
- `quantity` must be a positive integer within configured limits.
- Monetary values must be calculated by a server-side pricing service.
- The relationship between the unit price and line total must be validated.
- Avoid cascading deletion of order items when a catalogue product or variant is deleted. Use protected references or nullable references with snapshots, as appropriate.
- The exact definition of whether `unit_price` includes customization charges must be consistent across checkout, order details, staff screens and payment reconciliation.

### 5.3 OrderItemCustomization

**Module:** `apps/orders/models/order_item_customization.py`

This model stores a historical snapshot of each customization applied to an order item.

Recommended fields:

| Field | Purpose |
|---|---|
| `id` | Stable identifier |
| `order_item` | Parent order-item foreign key |
| `option_name_snapshot` | Name of the customization option |
| `choice_name_snapshot` | Selected choice |
| `value_snapshot` | Optional normalized value, where applicable |
| `price_adjustment` | Price adjustment captured for this selection |
| `created_at` | Creation timestamp |

Requirements:

- Use the normalized customization records from `apps.customization` to validate selections during checkout.
- Persist the selected option, selected choice, relevant value and price adjustment as order snapshots.
- Do not rely on live customization records to reconstruct an old order.
- Validate permitted choices and price adjustments before creating the order.
- Do not trust client-supplied customization prices.
- Avoid saving sensitive or unnecessary customer data in customization snapshots.
- Do not create a separate persistent customization-selection model in the orders app unless a concrete requirement justifies it.

### 5.4 OrderStatusHistory

**Module:** `apps/orders/models/order_status_history.py`

Records meaningful changes to the order lifecycle.

Recommended fields:

| Field | Purpose |
|---|---|
| `id` | Stable identifier |
| `order` | Related order |
| `from_status` | Previous status; nullable for initial creation |
| `to_status` | New status |
| `changed_by` | Authenticated actor, nullable for an authorized system action |
| `reason` | Optional reason for an administrative transition |
| `metadata` | Optional restricted, structured audit metadata |
| `created_at` | Transition timestamp |

Requirements:

- Create the initial history entry in the same database transaction as the order.
- Every permitted status change must create a history record.
- Status and history must be updated atomically.
- Do not expose unrestricted history mutation to customers.
- Record the responsible staff member for manual administrative transitions.
- Do not store full payment screenshots, credentials or unnecessary personal data in audit metadata.
- History must not be editable through ordinary customer-facing endpoints.
- Retain history with its parent order.

If the codebase has an existing shared audit mechanism, reuse it where appropriate without losing order-specific transition details.

## 6. Order Lifecycle

### 6.1 Order status

The initial status must represent an order awaiting manual payment verification.

Recommended lifecycle:

```text
PENDING_PAYMENT_VERIFICATION
             |
             | Staff verifies payment successfully
             v
         CONFIRMED
             |
             v
         PREPARING
             |
             v
       READY_FOR_PICKUP
             |
             v
         COMPLETED
```

The status values should be implemented as stable internal choices, with a consistent API representation.

| Status | Meaning |
|---|---|
| `pending_payment_verification` | Order exists, but staff has not yet verified the submitted payment evidence |
| `confirmed` | Payment has been verified and the order is accepted for fulfilment |
| `preparing` | Preparation has started |
| `ready_for_pickup` | The order is ready for customer collection |
| `completed` | The order has been collected and the order lifecycle is complete |
| `cancelled` | Reserved for authorized staff/system cancellation if that capability is later approved; not available to customers |

The `cancelled` status does not grant customers a cancellation capability. Customer cancellation is prohibited.

The exact handling of rejected payment evidence, failed payment verification, abandoned checkout, staff-initiated cancellation and exceptional refunds remains subject to explicit business policy. Do not invent automatic transitions for these cases.

### 6.2 Transition rules

Implement transitions in `services/status_transitions.py`.

The service must:

- Define the allowed source and destination statuses.
- Reject invalid or out-of-order transitions.
- Restrict transition permissions by actor type.
- Prevent customers from directly modifying order status.
- Ensure staff actions are authorized.
- Create history entries for successful transitions.
- Use a database transaction for each transition.
- Lock the order row when necessary to prevent concurrent state changes.
- Avoid sending notifications or performing external payment actions inside a database transaction.
- Return a domain-specific error for an invalid transition.

Staff must not be able to mark an order `confirmed` merely by changing an arbitrary status field. The service must require the corresponding payment-verification result from the payments domain.

### 6.3 Order status versus payment status

Order lifecycle and payment processing are separate state machines.

**Order status** answers: What stage is the order in?

**Payment status** answers: What is the state of the payment and its verification?

The payments app owns the authoritative payment record and payment-state transitions. Orders may expose a read-only payment summary or a synchronized payment-status field if the implementation requires it.

The payment lifecycle should support the states needed for manual UPI verification, such as awaiting evidence, awaiting staff verification, verified, rejected or failed. The final payment-state vocabulary belongs to the payments specification.

Rules:

- Uploading a screenshot does not constitute successful payment.
- A customer-provided reference ID or screenshot must never mark a payment verified automatically.
- An order cannot be confirmed until the required payment verification succeeds.
- A rejected screenshot must not silently confirm the order.
- Payment verification must not overwrite the order lifecycle indiscriminately.
- Payment callbacks or staff actions must be idempotent.
- If the payment result and order transition cannot be completed atomically across the involved records, use an explicit service workflow with locking, retries and reconciliation.
- Refunds, partial payments, multiple payment attempts and payment-verification rejection handling must follow the payments app's separately defined policies.

## 7. Checkout and Order Creation

**Module:** `apps/orders/services/checkout.py`

The checkout service is the only supported application-level path for creating an order from a cart.

### 7.1 Preconditions

Before creating an order, the service must verify:

1. The customer is authenticated.
2. The customer's cart belongs to that authenticated user.
3. The cart contains at least one valid item.
4. Each product and variant is still eligible for purchase.
5. Each customization is valid for its product and variant.
6. All quantities satisfy configured limits.
7. Prices are recalculated using current server-side data.
8. The currency is INR.
9. The customer has provided a valid phone number.
10. The optional email, if provided, is validated.
11. A pickup slot has been selected and is still available.
12. The configured tax and total-price policy is usable.
13. The checkout request is not a duplicate of an already processed request.
14. The payment workflow can create the required payment record for UPI QR verification.

The cart must be revalidated at checkout even if it was previously validated on the cart page.

### 7.2 Recommended creation sequence

1. Authenticate the customer.
2. Validate the checkout payload.
3. Acquire the relevant cart/order idempotency protection.
4. Load the customer's cart and required product, variant and customization data.
5. Revalidate purchase eligibility, quantities, customizations and prices.
6. Validate the selected pickup slot against current availability and lead-time rules.
7. Apply the configured pricing policy. If tax policy is still unconfigured, do not invent tax behavior or create an order with a misleading total.
8. Start a database transaction.
9. Lock or otherwise protect the cart and any relevant slot-capacity record.
10. Create the order with `pending_payment_verification`.
11. Create all order-item snapshots.
12. Create all customization snapshots.
13. Create the initial order-status history entry.
14. Create the corresponding payment record through the payments app's supported service boundary, with appropriate transactional coordination.
15. Reserve the pickup slot if the scheduling design requires capacity reservation.
16. Persist the idempotency result.
17. Commit the transaction.
18. Return the created order and the payment instructions needed for the next step.
19. Trigger any required notifications only after successful commit, using an after-commit mechanism or reliable event/outbox approach where appropriate.

The sequence may be adapted to the existing payment integration, but it must preserve atomicity and prevent duplicate orders or orphaned payment records.

### 7.3 Cart behavior after order creation

The cart app owns cart mutation and clearing.

After a successful order creation, the corresponding purchased cart state must not remain available for accidental duplicate checkout. The checkout workflow must coordinate cart consumption or clearing with order creation so a failure cannot leave a misleading partial state.

Do not clear the cart before the order transaction is safely committed.

Repeated requests with the same idempotency key must return the existing result when the original request has already succeeded. They must not create another order or payment record.

## 8. Pickup Scheduling

Customers choose a pickup slot during checkout, before submitting the order.

The selected slot must be persisted on the order so that later changes to scheduling configuration do not silently change an existing customer's selection.

Recommended fields:

- `pickup_slot_start`
- `pickup_slot_end`

The system should use timezone-aware datetimes and one explicitly configured business timezone. Pune/Maharashtra local time is a likely business requirement, but the application's timezone configuration must be verified rather than assumed.

### Required validation

- The selected slot must be offered by the scheduling system.
- The slot must be valid, not in the past and not already closed.
- The slot must satisfy the minimum lead time after ordering.
- The slot must have sufficient capacity if capacity limits are enabled.
- Concurrent checkout requests must not exceed slot capacity.
- The server, not the client, must decide whether a slot is available.
- The selected slot must be preserved in the order snapshot.
- If the selected slot becomes unavailable before submission, checkout must request a new slot rather than silently changing it.

### Scheduling policy still to be finalized

The business has specified that pickup should be available from approximately 30–45 minutes after ordering, but the exact minimum lead time has not been selected.

Before production implementation, define:

- The exact minimum preparation lead time.
- Pickup slot duration and interval.
- Store opening hours and closed days.
- Slot capacity and whether capacity depends on cake type or quantity.
- How staff handles delays or a full slot.
- Whether customers may request a slot farther in the future.

Do not hard-code assumptions about these rules across multiple views. Keep scheduling decisions in a dedicated scheduling service or a clearly isolated service boundary. A separate scheduling app is unnecessary until the complexity warrants it.

## 9. Pricing and Totals

All totals must be calculated on the server.

The client may display estimated totals, but client-supplied prices are never authoritative.

At checkout:

- Recalculate current base prices.
- Recalculate customization adjustments.
- Multiply validated unit amounts by the ordered quantity.
- Derive line totals and subtotal consistently.
- Keep currency fixed to INR.
- Store the agreed values in order snapshots.
- Reject stale or invalid cart state.
- Never trust a client-provided grand total, tax total or discount amount.

### Tax handling

Tax treatment is explicitly **undecided**.

Until the business establishes the tax policy, the system must not assume that taxes are included, calculate a tax rate from an invented configuration, or silently represent an unconfigured tax amount as zero.

Before enabling production checkout, the business must define the applicable tax treatment, how displayed prices relate to tax, and how the final amount is calculated. Implement the selected policy through a centralized pricing service.

### Discounts and promotions

Promotions and coupons are not supported at launch.

The architecture may leave room for future pricing extensions, but must not introduce unnecessary coupon tables, promotion engines or endpoints before a business requirement exists.

## 10. UPI Payment Integration Boundary

The launch payment method is a UPI QR code supplied by Leeza Cakes.

The intended customer flow is:

1. The customer signs in and checks out.
2. The customer selects a pickup slot and submits the order.
3. The order is created with payment awaiting staff verification.
4. The payment experience displays the configured UPI QR code and payment instructions.
5. The customer uploads a payment screenshot through the payment workflow.
6. Authorized staff reviews the evidence.
7. The payments app records the verification outcome.
8. On successful verification, the order workflow may transition to `confirmed`.
9. On rejection, the payment workflow records the rejection and the order remains in an appropriate non-confirmed state until the separately defined recovery policy is applied.

The `payments` app owns:

- UPI payment records.
- Payment attempts and references.
- Screenshot evidence metadata and secure file storage.
- Manual verification actions.
- Payment status and verification history.
- Payment-related staff permissions.
- Any future refund workflow.

The `orders` app owns the order and its lifecycle.

### Screenshot security

Payment screenshots are sensitive transaction evidence. They must not be stored in a public media directory or exposed through guessable URLs.

Use private object storage or an equivalently protected storage mechanism. Enforce file type and size limits, use server-side validation, and grant access only to the submitting customer where appropriate and authorized staff. Avoid trusting file extensions alone. Do not expose payment screenshots in public product or order listings.

Do not implement a fake payment gateway, assume screenshot authenticity, or claim automated UPI payment confirmation when the launch workflow is manual.

The exact QR-code configuration mechanism and the payment-evidence review/rejection policy must be defined in the payments specification.

## 11. API Responsibilities

Detailed request/response schemas belong in `backend/docs/apps/orders_api.md`.

Recommended API surface:

### Customer endpoints

| Method | Endpoint | Responsibility |
|---|---|---|
| `POST` | `/api/v1/orders/` | Create an order from the authenticated customer's validated cart |
| `GET` | `/api/v1/orders/` | List the authenticated customer's orders |
| `GET` | `/api/v1/orders/{order_id}/` | Retrieve one of the customer's orders |

The order-creation request should include only the data required for checkout, such as contact details, the selected pickup slot and an idempotency key. It must not accept authoritative order totals or lifecycle statuses.

Payment evidence upload and payment status actions belong to the payments API.

There is no customer cancellation endpoint.

A separate endpoint for changing a pickup slot should not be added until the business defines whether post-order rescheduling is permitted.

### Staff endpoints

Staff order-management endpoints should be separately permissioned and documented. They may support:

- Listing and filtering orders.
- Viewing full order details.
- Moving an order through allowed fulfilment statuses.
- Recording an authorized cancellation or exception, if that policy is approved.
- Viewing the order-status history.

Payment verification must be performed through the payments app, not by accepting an arbitrary payment-status field in an order-update request.

### API requirements

- Use DRF serializers for validation and representation.
- Use explicit permissions for customer and staff operations.
- Return only the authenticated customer's orders on customer endpoints.
- Use a consistent error response format.
- Use pagination for order lists.
- Avoid exposing internal storage paths, private evidence URLs or unnecessary audit metadata.
- Do not expose raw model fields indiscriminately.
- Keep public order references distinct from internal authorization.
- Use server-side filtering and ownership checks.
- Document endpoints in the project's OpenAPI schema.

## 12. Authorization and Data Isolation

### Customer access

Customers may:

- Create orders from their own carts.
- View their own order history.
- View their own order details.

Customers may not:

- Place orders without authentication.
- Access another customer's order by changing an ID.
- Change order or payment status.
- Change the recorded total.
- Confirm their own payment.
- Cancel an order.
- Modify order snapshots after creation.
- Access another customer's payment evidence.

### Staff access

Staff access must be based on explicit roles and permissions. Do not treat every authenticated user as staff.

Separate order-management permissions from payment-verification permissions where practical. Record the staff actor for privileged state changes.

Apply object-level authorization in the service/query layer as well as at the API boundary.

## 13. Transactions, Concurrency and Idempotency

Checkout must be designed for retries, double-clicks, network failures and concurrent requests.

Required protections:

- Use a database transaction for order and order-item creation.
- Create the initial status-history record atomically with the order.
- Use a unique, appropriately scoped idempotency key.
- Add database constraints for unique order numbers and other genuine invariants.
- Lock relevant records when concurrent changes could invalidate checkout.
- Prevent a cart from being consumed by two successful checkout requests.
- Prevent pickup-slot capacity from being exceeded when capacity limits are configured.
- Coordinate payment-record creation with order creation.
- Ensure a retry cannot create a second order or payment record.
- Ensure status transitions cannot race into invalid states.
- Use after-commit actions or a reliable event/outbox approach for external side effects.

Database constraints should enforce critical invariants even when requests bypass the expected application flow.

Do not depend solely on frontend button disabling for duplicate prevention.

## 14. Order Snapshots and Historical Integrity

An order is a historical commercial record, not a live view of the current catalogue.

At order creation, persist:

- Product name.
- Selected variant/size.
- Quantity.
- Base price.
- Customization selections and their labels.
- Customization price adjustments.
- Unit and line totals.
- Currency.
- Customer name and mandatory phone number.
- Optional customer email.
- Selected pickup-slot start and end.
- The agreed order totals under the configured pricing policy.

Historical order details must remain understandable if:

- A product is renamed.
- A variant is renamed or removed.
- A customization choice is changed or removed.
- A catalogue price changes.
- The customer updates their profile.
- A product becomes unpublished or archived.

Use protected or nullable references to live catalogue records where appropriate, while relying on snapshots for historical presentation.

Do not permit ordinary updates to order snapshots after creation. Any exceptional correction mechanism must be staff-only, audited and explicitly designed; financial corrections must not silently overwrite the original transaction history.

## 15. Retention, Deletion and Privacy

The confirmed initial policy is to retain historical orders without automatic deletion.

Requirements:

- Do not add scheduled jobs that automatically delete old orders.
- Do not cascade-delete historical orders when a customer account is deactivated or a catalogue object is removed.
- Use soft deletion or anonymization for other records only when justified and consistent with applicable obligations.
- Restrict access to customer contact details and payment evidence.
- Avoid storing unnecessary personal information.
- Keep audit metadata proportionate to operational needs.
- Do not log payment screenshots, authentication tokens or unnecessary personal data.

The formal legal and business retention period, archival rules and account-deletion/anonymization obligations remain undecided. The no-automatic-deletion rule is the launch behavior, not a substitute for a documented compliance policy.

## 16. Notifications and External Side Effects

The orders app may emit domain events or invoke a notification service after a successful state change. The `notifications` app owns actual delivery.

Potential events include:

- Order created.
- Payment verification completed.
- Order confirmed.
- Preparation started.
- Order ready for pickup.
- Order completed.
- Authorized exception or cancellation.

Do not send messages directly from model `save()` methods.

Prefer explicit service-layer events and after-commit dispatch. If reliable delivery is required, use an outbox or equivalent retryable mechanism rather than assuming that an in-process callback always succeeds.

Notification failures must not silently undo a successfully committed order.

The exact notification channels and message templates are owned by the notifications specification.

## 17. Django Admin

The Django admin may support authorized staff operations for:

- Searching by order number.
- Filtering by order status and creation date.
- Viewing customer contact snapshots.
- Viewing order items and customization snapshots.
- Viewing the pickup slot.
- Viewing order-status history.
- Inspecting the linked payment summary where permissions permit.

Administrative actions must use the same domain services and transition rules as API operations. Do not allow unrestricted direct status edits that bypass validation, audit history or payment verification.

Payment screenshot access must follow the payments app's authorization and secure-storage rules.

## 18. Testing Requirements

The order app is not ready for production until its business invariants are covered by automated tests.

### Order creation

- Authenticated customer can create an order from a valid cart.
- Unauthenticated customer cannot create an order.
- Empty cart is rejected.
- Guest cart cannot be used to place an order without authentication and a valid authenticated-cart association.
- Invalid or unpublished product is rejected.
- Invalid variant is rejected.
- Invalid customization is rejected.
- Invalid quantity is rejected.
- Missing phone number is rejected.
- Invalid optional email is rejected.
- Invalid or unavailable pickup slot is rejected.
- Checkout does not accept client-supplied authoritative totals.
- Unconfigured tax policy does not silently produce a misleading total.

### Snapshots and totals

- Product and variant names are snapshotted.
- Customization labels and price adjustments are snapshotted.
- Totals are calculated using decimal arithmetic.
- Currency is INR.
- Historical snapshots remain unchanged after catalogue edits.
- Historical order display does not require live catalogue objects to exist.
- Customer profile changes do not overwrite contact snapshots.

### Lifecycle and payment

- New orders start in `pending_payment_verification`.
- A screenshot alone does not confirm an order.
- Only an authorized payment-verification result can permit confirmation.
- Order status and payment status remain independent.
- Invalid status transitions are rejected.
- Customers cannot cancel orders.
- Unauthorized users cannot perform staff transitions.
- Status history is created atomically.
- Concurrent transitions cannot produce invalid states.

### Idempotency and concurrency

- Repeated checkout with the same idempotency key does not create duplicate orders.
- Concurrent checkout requests do not consume the same cart twice.
- Failed transactions do not leave partial order items or misleading payment records.
- Pickup-slot capacity is respected if capacity is implemented.
- Retried post-commit actions do not duplicate order creation.

### Authorization and retention

- Customer order lists contain only that customer's orders.
- Customer detail endpoints deny access to other customers' orders.
- Staff operations require explicit permission.
- Historical orders are not automatically deleted.
- Private payment evidence is not exposed by order serializers.

Use the repository's existing test conventions and factories. Avoid live payment operations, external notification delivery or production database access in ordinary unit tests.

## 19. Observability and Error Handling

Use structured logging for meaningful order events, including:

- Order creation success/failure.
- Invalid checkout attempts.
- Idempotency replays.
- Failed or rejected state transitions.
- Payment/order synchronization failures.
- Pickup-slot conflicts.
- Transaction failures.

Include safe correlation identifiers such as internal order IDs or order numbers where appropriate.

Never log payment screenshots, secrets, authentication tokens or unnecessary personal data.

Errors should be actionable and safe for the client. Do not expose stack traces, raw database errors or internal storage paths through the API.

Operational failures between orders and payments must be detectable and recoverable. Provide an explicit reconciliation mechanism if the integration can leave a payment record and order in inconsistent states.

## 20. Implementation Order

Implement the app in this sequence:

1. Confirm the configured user model and authentication behavior.
2. Finalize the order and order-item models.
3. Implement immutable order and customization snapshots.
4. Define order and payment state boundaries with the payments app.
5. Implement centralized pricing and checkout validation.
6. Implement pickup-slot validation and reservation behavior.
7. Implement transactional, idempotent order creation.
8. Implement status-transition services and history.
9. Implement customer order-list and detail selectors.
10. Implement customer API endpoints.
11. Implement staff operations with explicit permissions.
12. Integrate payment screenshot verification through `apps.payments`.
13. Integrate notifications through `apps.notifications`.
14. Add tests for business rules, concurrency, authorization and failure cases.
15. Validate OpenAPI documentation and run the repository's quality checks.

Do not run migrations until the required model decisions and migration plan are reviewed and explicitly approved. Do not run migrations against production or alter production data without explicit approval.

## 21. Explicitly Undecided Policies

The following matters must remain visible as unresolved decisions. The implementation must not invent answers.

| Decision | Current position | Required before |
|---|---|---|
| Tax treatment | Unconfigured; no assumed inclusion, rate or zero-tax behavior | Production checkout |
| Exact pickup lead time | Approximately 30–45 minutes; exact minimum not selected | Scheduling implementation |
| Pickup-slot duration and interval | Not decided | Scheduling implementation |
| Store opening hours and closed days | Not decided | Scheduling implementation |
| Pickup capacity and reservation rules | Not decided | Reliable slot booking |
| Handling rejected payment evidence | Not decided | Complete payment workflow |
| Payment retry or replacement-evidence policy | Not decided | Complete payment workflow |
| Staff cancellation and exceptional refunds | Customer cancellation prohibited; staff policy not decided | Staff exception workflow |
| Formal retention and archival period | Keep orders; no automatic deletion | Compliance and lifecycle policy |
| Order/payment reconciliation policy | Required where failures can create inconsistent records; operational procedure not finalized | Production readiness |
| Exact business timezone | Must be explicitly configured and verified | Scheduling implementation |

These undecided policies do not authorize arbitrary defaults. Use explicit configuration, validation failures or a disabled feature until the relevant decision is approved.

## 22. Definition of Done

The orders app is ready for production review only when:

- Order creation requires authentication.
- Checkout validates the current cart, products, variants and customizations.
- Customer phone is mandatory and email is optional.
- The pickup slot is selected during checkout and validated server-side.
- The configured pricing policy is complete, including tax handling.
- The order starts in `pending_payment_verification`.
- UPI screenshot evidence is handled by the payments app and stored securely.
- Manual payment verification is required before order confirmation.
- Order and payment states remain separate.
- Customer cancellation is unavailable.
- Order and customization snapshots preserve historical information.
- Checkout is transactional and idempotent.
- Customer ownership and staff permissions are enforced.
- Status history is maintained.
- Historical orders are not automatically deleted.
- Automated tests cover the defined business invariants.
- OpenAPI documentation matches the implemented API.
- No migration or production-data operation has been performed without approval.

**Architecture principle:** `orders` owns the durable commercial order and its fulfilment lifecycle. `payments` owns payment evidence and verification. `cart` owns the mutable shopping session. Historical order snapshots preserve what the customer ordered and the prices agreed upon at checkout.