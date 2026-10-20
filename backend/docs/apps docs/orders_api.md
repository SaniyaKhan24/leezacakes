# Orders API — Leeza Cakes

**Project:** Leeza Cakes  
**Path:** `backend/docs/apps/orders_api.md`  
**App:** `apps.orders`  
**Base path:** `/api/v1/orders/`  
**API style:** Django REST Framework  
**Currency:** INR  
**Fulfilment:** Customer pickup only  
**Status:** API specification

---

## 1. Purpose

The Orders API lets authenticated customers create orders from their validated carts, select a pickup slot during checkout, and view their own order history and order details.

It also provides authorized staff with order-management operations.

The API must follow the rules defined in `backend/docs/apps/orders_structure.md`. This document defines endpoint behavior, payloads, permissions, validation, response shapes, errors and testing requirements.

### Confirmed business rules

- Authentication is mandatory to place an order.
- Guest customers may use carts but cannot place orders.
- Phone number is mandatory; email is optional.
- UPI QR payment is the only launch payment method.
- Customers must upload a payment screenshot for manual verification through the payments app.
- A new order starts with `pending_payment_verification`.
- Payment status and order status are separate.
- Customers cannot cancel submitted orders.
- Pickup-slot selection occurs during checkout, before order submission.
- Pickup should begin approximately 30–45 minutes after ordering, but the exact minimum lead time remains undecided.
- Home delivery, cash on pickup, promotions and coupons are out of scope for launch.
- INR is the only supported currency.
- Tax handling remains unconfigured until the business defines the policy.
- Historical orders must not be automatically deleted.

## 2. API Conventions

### Authentication

Customer endpoints require an authenticated user. Use the authentication mechanism already configured for the project.

Do not introduce a second authentication system specifically for orders.

Staff endpoints require the appropriate staff role or explicit permission. Authentication alone does not grant staff access.

### Content types

- Requests containing JSON: `application/json`
- Multipart uploads: handled by the payments API, not the Orders API.
- Responses: `application/json`

### Identifiers

Use the existing project convention for internal order identifiers, preferably UUIDs if that is the chosen model design.

The customer-facing `order_number` is a reference, not an authorization token. Knowing an order number or UUID must not grant access to the order.

### Pagination

Order-list endpoints must use the project's configured pagination conventions.

### Timestamps

Return ISO 8601 timestamps with timezone information. The application must use an explicitly configured business timezone for pickup scheduling.

### Monetary values

Represent monetary amounts as decimal strings in JSON responses, for example `"1250.00"`. Never use floating-point arithmetic for monetary calculations.

All order amounts use INR.

## 3. Endpoint Summary

### Customer endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/orders/` | Create an order from the authenticated customer's cart |
| `GET` | `/api/v1/orders/` | List the authenticated customer's orders |
| `GET` | `/api/v1/orders/{order_id}/` | Retrieve one of the authenticated customer's orders |

### Staff endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/orders/staff/` | List and filter orders for authorized staff |
| `GET` | `/api/v1/orders/staff/{order_id}/` | Retrieve full order details for authorized staff |
| `POST` | `/api/v1/orders/staff/{order_id}/transitions/` | Request an allowed order-status transition |

The staff routes are suggestions for the target API. If the existing project uses a different administrative URL convention, maintain a consistent staff-only namespace without changing the permission requirements.

Payment verification, payment screenshot upload and payment-status changes belong to the `payments` API.

There is **no customer cancellation endpoint**.

## 4. Create Order

`POST /api/v1/orders/`

Creates an order from the authenticated customer's current cart.

The server must load and validate the cart. The request must not contain authoritative product prices, line totals, order totals or status values.

### Authentication

Required.

### Headers

```http
Authorization: <configured authentication credentials>
Content-Type: application/json
Idempotency-Key: <unique client-generated key>
```

The exact authorization header depends on the project's configured authentication mechanism. Do not hard-code a particular scheme in this specification if the application uses a different one.

`Idempotency-Key` is required for checkout. The server must scope and persist the key appropriately so retries cannot create duplicate orders.

### Request body

```json
{
  "customer_name": "Customer Name",
  "customer_phone": "+919876543210",
  "customer_email": "customer@example.com",
  "pickup_slot_start": "2026-11-01T14:30:00+05:30",
  "pickup_slot_end": "2026-11-01T14:45:00+05:30",
  "customer_note": "Please write Happy Birthday on the cake."
}
```

Field requirements:

| Field | Type | Required | Rules |
|---|---|---|---|
| `customer_name` | String | Yes | Non-empty after trimming; enforce configured length limits |
| `customer_phone` | String | Yes | Validated phone number; preserve a normalized representation |
| `customer_email` | String or `null` | No | Validate when supplied; optional |
| `pickup_slot_start` | ISO 8601 datetime | Yes | Must match a valid available slot |
| `pickup_slot_end` | ISO 8601 datetime | Yes | Must match the corresponding slot interval |
| `customer_note` | String or `null` | No | Optional, length-limited and sanitized according to project conventions |

The exact pickup-slot representation may be replaced by a slot identifier if a dedicated scheduling service is implemented. If a slot identifier is used, the server must still validate that the slot exists, is available and matches the requested interval.

The client must not submit:

- `user`
- `order_number`
- `status`
- `payment_status`
- `subtotal`
- `tax_total`
- `discount_total`
- `grand_total`
- `currency`
- Product prices
- Customization prices
- Arbitrary cart IDs
- Payment verification results

The cart app is responsible for resolving the authenticated customer's cart.

### Server-side processing

The endpoint must:

1. Authenticate the customer.
2. Validate the request body.
3. Resolve the customer's active cart.
4. Revalidate every cart item, product, variant, quantity and customization.
5. Recalculate all prices from trusted server-side data.
6. Validate the pickup slot, lead time and availability.
7. Apply the configured tax and pricing policy.
8. Reject checkout if required pricing configuration is missing.
9. Create the order and snapshots transactionally.
10. Create the initial order-status history entry.
11. Coordinate creation of the corresponding payment record with `apps.payments`.
12. Protect against concurrent checkout and duplicate requests.
13. Consume or clear the purchased cart only after the order workflow commits successfully.
14. Return the created order and the payment instructions or next-step information supported by the payments API.

The endpoint must not mark the order confirmed merely because the customer submitted the checkout request.

### Successful response

HTTP `201 Created`.

```json
{
  "id": "9d8f1a44-64f1-4d7f-9bb8-28f0c6c69a10",
  "order_number": "LZ-2026-000123",
  "status": "pending_payment_verification",
  "payment": {
    "status": "pending_verification",
    "method": "upi_qr",
    "next_step": "upload_payment_screenshot"
  },
  "customer": {
    "name": "Customer Name",
    "phone": "+919876543210",
    "email": "customer@example.com"
  },
  "pickup": {
    "slot_start": "2026-11-01T14:30:00+05:30",
    "slot_end": "2026-11-01T14:45:00+05:30"
  },
  "currency": "INR",
  "subtotal": "1200.00",
  "discount_total": "0.00",
  "tax_total": null,
  "grand_total": null,
  "items": [
    {
      "id": "5fdfd7b0-f4c1-46e4-a70e-a62c1f8e7c21",
      "product_name": "Chocolate Cake",
      "variant_name": "1 kg",
      "quantity": 1,
      "unit_base_price": "1200.00",
      "unit_customization_total": "0.00",
      "unit_price": "1200.00",
      "line_total": "1200.00",
      "customizations": []
    }
  ],
  "created_at": "2026-11-01T13:50:00+05:30"
}
```

**Important:** The response above illustrates the response shape, not permission to accept an order while tax policy is unconfigured. Until the business approves a valid pricing/tax policy, checkout must fail safely rather than return an order with a misleading or incomplete payable amount. In production, `grand_total` must be a valid calculated amount before an order can be submitted.

If email was omitted, return `null` or omit the field consistently according to the project's API convention.

The payment object is a read-only summary. Its final fields and status vocabulary must align with `apps.payments`.

### Possible errors

- `400 Bad Request`: invalid contact information, malformed request, invalid slot or validation failure.
- `401 Unauthorized`: authentication missing or invalid.
- `403 Forbidden`: user is not permitted to perform the operation.
- `409 Conflict`: stale cart, unavailable slot, price conflict, or idempotency conflict that cannot be replayed as the original result.
- `422 Unprocessable Entity`: may be used for domain validation errors if consistent with project conventions.
- `429 Too Many Requests`: rate limit exceeded, if configured.
- `500 Internal Server Error`: unexpected failure; never expose internal exception details.

Use one consistent error convention across the API. Do not return different status codes for the same domain condition without a documented reason.

## 5. Idempotent Checkout

Checkout requests may be repeated due to retries, network failures or users clicking submit more than once.

Requirements:

- Require an idempotency key for order creation.
- Scope the key to the authenticated customer and checkout operation.
- Persist the key and the result of a successful request.
- Reuse the original result for an identical retry.
- Reject reuse of the same key for a materially different payload.
- Ensure a retry cannot create a second order or payment record.
- Protect against concurrent requests using database constraints and appropriate transaction handling.
- Do not rely only on frontend button disabling.

The precise storage model can be implemented using an idempotency record or an equivalent database-enforced design.

## 6. List Customer Orders

`GET /api/v1/orders/`

Returns a paginated list of orders belonging to the authenticated customer.

### Authentication

Required.

### Optional query parameters

| Parameter | Type | Purpose |
|---|---|---|
| `status` | String | Filter by order lifecycle status |
| `page` | Integer | Page number, if supported by the configured pagination |
| `page_size` | Integer | Page size, subject to server-side maximum |
| `ordering` | String | Supported ordering, preferably creation date |

Only explicitly supported filters should be exposed. Validate every query parameter and reject unsupported ordering fields where appropriate.

### Successful response

HTTP `200 OK`.

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "9d8f1a44-64f1-4d7f-9bb8-28f0c6c69a10",
      "order_number": "LZ-2026-000123",
      "status": "pending_payment_verification",
      "payment_status": "pending_verification",
      "currency": "INR",
      "grand_total": "1200.00",
      "item_count": 1,
      "pickup_slot_start": "2026-11-01T14:30:00+05:30",
      "pickup_slot_end": "2026-11-01T14:45:00+05:30",
      "created_at": "2026-11-01T13:50:00+05:30"
    }
  ]
}
```

The payment status is read-only and must reflect the payments domain's authoritative state. If no payment status is available yet, the API must represent that state consistently rather than inventing one.

Do not include private payment evidence or excessive customer information in list responses.

## 7. Retrieve Customer Order

`GET /api/v1/orders/{order_id}/`

Returns the full order representation for the authenticated customer who owns the order.

### Authentication

Required.

### Successful response

HTTP `200 OK`.

The response should contain:

- Order identifier and order number.
- Current order status.
- Read-only payment summary.
- Customer contact snapshot.
- Pickup-slot snapshot.
- Currency and valid monetary totals.
- Order-item snapshots.
- Customization snapshots.
- Creation and relevant lifecycle timestamps.
- A safe, read-only status-history summary if customer visibility is approved.

Example:

```json
{
  "id": "9d8f1a44-64f1-4d7f-9bb8-28f0c6c69a10",
  "order_number": "LZ-2026-000123",
  "status": "confirmed",
  "payment": {
    "status": "verified",
    "method": "upi_qr"
  },
  "customer": {
    "name": "Customer Name",
    "phone": "+919876543210",
    "email": null
  },
  "pickup": {
    "slot_start": "2026-11-01T14:30:00+05:30",
    "slot_end": "2026-11-01T14:45:00+05:30"
  },
  "currency": "INR",
  "subtotal": "1200.00",
  "discount_total": "0.00",
  "tax_total": null,
  "grand_total": "1200.00",
  "items": [
    {
      "product_name": "Chocolate Cake",
      "variant_name": "1 kg",
      "quantity": 1,
      "unit_price": "1200.00",
      "line_total": "1200.00",
      "customizations": []
    }
  ],
  "created_at": "2026-11-01T13:50:00+05:30",
  "confirmed_at": "2026-11-01T14:00:00+05:30"
}
```

The values above are illustrative. A real response must never fabricate a confirmation timestamp or expose an uncalculated tax total. If the tax policy remains unconfigured, checkout should be disabled until the required total can be calculated correctly.

### Authorization

- Return `404 Not Found` for an order that does not exist or does not belong to the customer, if that is the project's chosen anti-enumeration convention.
- Never authorize access based solely on `order_number`.
- Do not expose payment screenshots through this endpoint.

## 8. Staff: List and Filter Orders

`GET /api/v1/orders/staff/`

Returns a paginated list of orders for authorized staff.

### Permissions

Require an explicit staff permission for viewing orders.

### Suggested filters

- `status`
- `payment_status` — only if exposed as a read-only payment-domain filter
- `order_number`
- `created_after`
- `created_before`
- `pickup_date`
- `pickup_slot_start`
- `pickup_slot_end`

All filters must be validated and indexed where query volume warrants it.

### Successful response

HTTP `200 OK`.

Use a staff-specific serializer that provides operationally useful details without exposing unnecessary secrets or unrestricted payment evidence.

Staff order lists must not allow arbitrary query parameters to bypass authorization or produce unbounded queries.

## 9. Staff: Retrieve Order Details

`GET /api/v1/orders/staff/{order_id}/`

Returns the full operational view of an order to authorized staff.

The response may include:

- Order number and lifecycle status.
- Customer contact snapshots.
- Pickup-slot details.
- Order-item and customization snapshots.
- Monetary breakdown.
- Read-only payment summary.
- Order-status history.
- Relevant timestamps.

Payment screenshot viewing must remain governed by the payments app's permissions and private-storage mechanism. The order serializer must not return public or guessable screenshot URLs.

## 10. Staff: Order Status Transition

`POST /api/v1/orders/staff/{order_id}/transitions/`

Requests a permitted order-lifecycle transition.

### Authentication and permissions

Require an authenticated staff user with the specific order-management permission.

Payment verification remains a separate operation in `apps.payments`. This endpoint must not accept a payment status or act as a shortcut for verifying payment.

### Request body

```json
{
  "to_status": "preparing",
  "reason": "Preparation started."
}
```

Field rules:

| Field | Type | Required | Rules |
|---|---|---|---|
| `to_status` | String | Yes | Must be an allowed destination for the current status and actor |
| `reason` | String | No | Optional, length-limited reason for an authorized transition |

The client must not submit `from_status`, `changed_by`, timestamps or arbitrary audit metadata.

### Allowed transitions

The service must enforce the lifecycle defined in `orders_structure.md`.

| Current status | Destination | Requirement |
|---|---|---|
| `pending_payment_verification` | `confirmed` | Successful payment verification must be established through the payments domain |
| `confirmed` | `preparing` | Authorized staff action |
| `preparing` | `ready_for_pickup` | Authorized staff action |
| `ready_for_pickup` | `completed` | Authorized staff action confirming collection |
| Any status | `cancelled` | Not available by default; requires an explicitly approved staff exception policy |

Do not permit arbitrary transitions just because the caller has staff access.

### Successful response

HTTP `200 OK`.

```json
{
  "id": "9d8f1a44-64f1-4d7f-9bb8-28f0c6c69a10",
  "order_number": "LZ-2026-000123",
  "status": "preparing",
  "updated_at": "2026-11-01T14:10:00+05:30"
}
```

The service must update the order and append its status-history record atomically.

### Errors

- `400 Bad Request`: malformed or missing transition data.
- `401 Unauthorized`: authentication missing or invalid.
- `403 Forbidden`: insufficient staff permission.
- `404 Not Found`: order does not exist.
- `409 Conflict`: invalid transition or concurrent state change.
- `500 Internal Server Error`: unexpected failure, without internal diagnostic details.

## 11. Payment API Boundary

The following operations are deliberately **not** implemented by the Orders API:

- Retrieving or displaying the configured UPI QR code.
- Uploading payment screenshots.
- Validating payment-evidence file content.
- Recording transaction references.
- Verifying or rejecting payment evidence.
- Changing payment status.
- Processing refunds.
- Exposing private payment evidence.

These operations belong to `apps.payments`.

Orders may expose a safe payment summary containing the payment method and current status, but the payments app remains authoritative.

The payments specification must define its own endpoints and evidence-retention/access policy. Orders must not duplicate those endpoints.

## 12. No Customer Cancellation or Rescheduling Endpoint

Customers cannot cancel submitted orders. Do not implement any of the following:

- `POST /api/v1/orders/{order_id}/cancel/`
- `DELETE /api/v1/orders/{order_id}/`
- A generic customer `PATCH` that allows changing `status`.

Post-order pickup rescheduling has not been approved. Do not implement a customer rescheduling endpoint until the business defines whether rescheduling is allowed, its deadline and how slot capacity is handled.

Staff exception handling must remain unavailable until its policy and permissions are explicitly specified.

## 13. Error Response Convention

Use the project's existing common exception and error-response format. The following is a conceptual example, not a mandate to introduce a second error format:

```json
{
  "error": {
    "code": "pickup_slot_unavailable",
    "message": "The selected pickup slot is no longer available.",
    "details": {
      "pickup_slot_start": [
        "Select another available pickup slot."
      ]
    }
  }
}
```

Error codes should be stable and suitable for frontend handling.

Recommended domain errors include:

| Code | Meaning |
|---|---|
| `authentication_required` | Authentication is required |
| `invalid_checkout_data` | Checkout fields are invalid |
| `cart_empty` | No items are available for checkout |
| `cart_changed` | Cart state changed and must be reviewed |
| `product_unavailable` | A product or variant is no longer purchasable |
| `customization_invalid` | A customization is no longer valid |
| `pickup_slot_unavailable` | The selected slot cannot be reserved |
| `pricing_configuration_missing` | Required pricing or tax policy is not configured |
| `idempotency_conflict` | A key was reused for a different request |
| `invalid_order_transition` | The requested lifecycle transition is not allowed |
| `permission_denied` | The caller lacks the required permission |

Do not expose raw database errors, stack traces, private storage details or payment-evidence content.

## 14. Validation and Security Requirements

- Validate every request with DRF serializers.
- Recalculate prices on the server.
- Validate all products, variants, customizations and quantities at checkout.
- Require authentication and enforce customer ownership on every customer order endpoint.
- Enforce explicit staff permissions for staff routes.
- Keep order and payment states separate.
- Prevent customer-supplied status or total changes.
- Require idempotency for order creation.
- Apply database constraints for critical invariants.
- Validate pickup-slot availability server-side.
- Use private storage and payments-app authorization for screenshots.
- Do not allow public order retrieval by order number alone.
- Do not log authentication credentials, private screenshots or unnecessary personal data.
- Rate-limit sensitive endpoints where appropriate.
- Use HTTPS in production.
- Avoid leaking whether another customer's order exists.

## 15. OpenAPI Documentation

Document all implemented endpoints in the project's OpenAPI schema.

For each endpoint, specify:

- Authentication and permission requirements.
- Request schema.
- Response schema.
- Status codes and error format.
- Pagination and filtering behavior.
- Idempotency requirements.
- Ownership and staff-authorization rules.
- Whether monetary values may be `null` or are guaranteed to be populated.

Use separate customer and staff serializers. Do not expose every model field by default.

The documented API must match actual behavior. Do not document future or disabled functionality as if it were available.

## 16. Testing Requirements

### Create-order tests

- Authenticated customer can submit a valid order.
- Unauthenticated customer cannot submit an order.
- Guest carts cannot be used to bypass the authentication requirement.
- Empty cart is rejected.
- Invalid product, variant or customization is rejected.
- Invalid quantity is rejected.
- Missing phone number is rejected.
- Email is optional but validated when provided.
- Invalid or unavailable pickup slot is rejected.
- Checkout ignores client-supplied prices and totals.
- Checkout fails safely when required tax/pricing configuration is missing.
- Successful creation starts in `pending_payment_verification`.
- Order and item snapshots are persisted.
- Initial status history is created atomically.
- Cart consumption is consistent with successful order creation.

### Idempotency and concurrency tests

- Retrying an identical request returns the original result.
- Reusing a key with a different payload is rejected.
- Concurrent requests cannot create duplicate orders.
- A failed transaction does not leave a partial order.
- A failed transaction does not leave an orphaned payment record.
- Slot capacity is respected if capacity limits are implemented.

### Customer authorization tests

- A customer can list only their own orders.
- A customer cannot retrieve another customer's order.
- Guessing an order ID or order number does not bypass ownership checks.
- Customers cannot change order status.
- No customer cancellation route is available.
- Payment screenshots are not returned in order responses.

### Staff tests

- Non-staff users cannot access staff endpoints.
- Staff users without the specific permission are denied.
- Invalid status transitions are rejected.
- Confirmation requires successful payment verification.
- Status history is written atomically.
- Concurrent transitions cannot corrupt order state.
- Staff actions record the responsible actor.

### Payment integration tests

- Payment status is read from or synchronized with the payments domain.
- Uploading a screenshot does not automatically verify payment.
- A successful verification permits the appropriate order transition.
- A rejected verification does not confirm the order.
- Duplicate payment events do not duplicate transitions or notifications.

### API schema tests

- OpenAPI includes all implemented routes.
- Request and response schemas match serializers.
- Authentication and permissions are documented.
- Error responses are documented.
- Disabled features are not exposed as available endpoints.

## 17. Unresolved Policies and Implementation Gates

The following policies remain undecided and must not be guessed during implementation.

| Policy | Current state | Required action |
|---|---|---|
| Tax calculation and price presentation | Unconfigured | Define the tax policy before enabling checkout |
| Exact pickup lead time | Approximately 30–45 minutes; exact minimum not selected | Define the minimum and enforce it centrally |
| Slot interval, opening hours and capacity | Not decided | Finalize the scheduling rules |
| Payment evidence rejection and retry behavior | Not decided | Define the payment workflow in `apps.payments` |
| Staff cancellation and exceptional refunds | No customer cancellation; staff exceptions not approved | Define explicit staff policy and permissions |
| Historical retention period and archival obligations | No automatic deletion | Establish formal retention and compliance rules |
| Payment/order reconciliation procedure | Operational procedure not finalized | Define recovery and reconciliation for inconsistent states |
| Business timezone | Must be explicitly configured and verified | Configure before scheduling goes live |

These gates must be resolved before the corresponding production functionality is enabled. In particular, the API must not create an order with a misleading payable amount while the required pricing policy is missing.

## 18. Definition of Done

The Orders API is ready for production review when:

- Authenticated checkout is implemented.
- Contact validation requires a phone number and allows an optional email.
- Pickup selection is required during checkout and validated server-side.
- The tax/pricing policy is configured before checkout is enabled.
- Order creation is transactional and idempotent.
- The initial order state is `pending_payment_verification`.
- Payment evidence and verification remain owned by `apps.payments`.
- Order and payment statuses are independent.
- Customer order history and detail access enforce ownership.
- Customer cancellation is not exposed.
- Staff transitions are permissioned, validated and audited.
- Order and customization snapshots preserve historical details.
- API errors follow a consistent project convention.
- OpenAPI documentation matches the implementation.
- Automated tests cover authorization, state transitions, checkout, idempotency, payment integration and failure cases.
- No migrations or production-data changes have been run without explicit approval.

**Architecture rule:** The Orders API creates and exposes durable orders. The Cart API manages mutable cart contents. The Payments API owns UPI evidence and verification. The Catalog and Customization apps own the current product configuration. Orders preserve the historical values agreed upon at checkout.