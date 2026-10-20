# Payments API — Leeza Cakes

**Project:** Leeza Cakes  
**Path:** `backend/docs/apps/payments_api.md`  
**App:** `apps.payments`  
**Base path:** `/api/v1/payments/`  
**Framework:** Django REST Framework  
**Currency:** INR  
**Launch payment method:** Fixed UPI QR with manual verification  
**Status:** API specification

---

## 1. Purpose

The Payments API manages payment records associated with Leeza Cakes orders, displays the configured UPI payment instructions, accepts payment screenshots, supports resubmission after rejection, and provides authorized staff with manual verification operations.

The API must follow `backend/docs/apps/payments_structure.md`.

### Confirmed rules

- One fixed Leeza Cakes UPI QR code is used at launch.
- Customers must pay the full exact order total.
- Payment screenshots are mandatory for every submission.
- Screenshot upload happens after order creation.
- Payment verification is performed manually by designated staff with explicit permission.
- A rejected screenshot may be replaced by a new submission.
- Payment status and order status are independent.
- Only successful manual verification may permit an order to become confirmed.
- Customers cannot cancel orders.
- Cash on pickup, partial payments and refunds are not supported at launch.
- Pending payments do not expire automatically.
- INR is the only supported currency.
- Payment screenshots must be stored privately.

## 2. Authentication and Permissions

Customer endpoints require authentication and object-level ownership checks.

Staff verification endpoints require an explicit permission, such as `payments.verify_payment`. Being authenticated or having general staff access is not sufficient.

| Role | Permitted operations |
|---|---|
| Authenticated customer | View own payment instructions and status; submit evidence for own payment; view own submission history; resubmit after rejection |
| Designated payment reviewer | View authorized payment records and evidence; accept or reject submissions; verify payments |
| Other authenticated users | No access to another customer's payments or evidence |
| Anonymous user | No access to payment records, submissions or evidence |

Use the project's configured authentication mechanism. Do not introduce a separate authentication system for payments.

## 3. Endpoint Summary

### Customer endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/payments/orders/{order_id}/` | Retrieve payment instructions and status for an order owned by the customer |
| `GET` | `/api/v1/payments/{payment_id}/` | Retrieve the customer's payment details and status |
| `GET` | `/api/v1/payments/{payment_id}/submissions/` | List the customer's own payment submissions and review outcomes |
| `POST` | `/api/v1/payments/{payment_id}/submissions/` | Upload mandatory screenshot evidence |
| `GET` | `/api/v1/payments/{payment_id}/submissions/{submission_id}/` | Retrieve one of the customer's own submission records |

### Staff endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/payments/staff/` | List and filter payments for authorized reviewers |
| `GET` | `/api/v1/payments/staff/{payment_id}/` | Retrieve payment details for authorized reviewers |
| `GET` | `/api/v1/payments/staff/{payment_id}/submissions/` | List submission evidence and review history |
| `POST` | `/api/v1/payments/staff/{payment_id}/submissions/{submission_id}/review/` | Accept or reject a submission |
| `POST` | `/api/v1/payments/staff/{payment_id}/verify/` | Record successful manual payment verification |
| `GET` | `/api/v1/payments/staff/{payment_id}/submissions/{submission_id}/evidence/` | Access evidence through an authorized private-storage operation |

These are the target routes. Adapt route organization to existing project conventions if necessary, without weakening permissions or separating a verification decision from its audit trail.

The fixed QR code may be included in the payment-instructions response. A separate public QR endpoint is not necessary unless the frontend architecture requires one.

## 4. Retrieve Payment Instructions

`GET /api/v1/payments/orders/{order_id}/`

Returns the payment instructions and current payment status for an order belonging to the authenticated customer.

### Authentication

Required.

### Successful response

HTTP `200 OK`.

```json
{
  "id": "2c914a64-8c9f-45a7-8bc2-0123456789ab",
  "order_id": "9d8f1a44-64f1-4d7f-9bb8-28f0c6c69a10",
  "order_number": "LZ-2026-000123",
  "method": "upi_qr",
  "status": "awaiting_payment",
  "amount_due": "1200.00",
  "currency": "INR",
  "payment_instructions": {
    "qr_code_url": "https://example.invalid/configured-public-qr.png",
    "payee_name": "Leeza Cakes",
    "instructions": "Pay the exact amount shown and upload your payment screenshot."
  },
  "can_submit_evidence": true,
  "created_at": "2026-11-01T13:50:00+05:30"
}
```

The URL above is a placeholder illustrating the response shape, not a real QR asset URL. The implementation must use the configured and verified QR asset.

### Requirements

- Verify that the order belongs to the authenticated customer.
- Return the expected amount from the trusted payment record.
- Return INR as the currency.
- Return only the configured UPI QR code and approved payment instructions.
- Do not accept a client-supplied amount or QR asset URL.
- Do not claim that the QR code itself verifies payment.
- Do not expose private screenshot URLs in this response.
- Set `can_submit_evidence` based on the current payment state and the resubmission rules.

If the order does not exist or belongs to another customer, return `404 Not Found` if that is the project's chosen anti-enumeration convention.

## 5. Retrieve Payment Details

`GET /api/v1/payments/{payment_id}/`

Returns the payment record belonging to the authenticated customer.

### Successful response

HTTP `200 OK`.

```json
{
  "id": "2c914a64-8c9f-45a7-8bc2-0123456789ab",
  "order_id": "9d8f1a44-64f1-4d7f-9bb8-28f0c6c69a10",
  "order_number": "LZ-2026-000123",
  "method": "upi_qr",
  "status": "pending_verification",
  "amount_due": "1200.00",
  "currency": "INR",
  "latest_submission": {
    "id": "72e5904b-cf1b-4a2e-bde8-b25d4c4d5c91",
    "status": "pending_review",
    "submitted_at": "2026-11-01T13:55:00+05:30"
  },
  "verified_at": null,
  "created_at": "2026-11-01T13:50:00+05:30",
  "updated_at": "2026-11-01T13:55:00+05:30"
}
```

The response must not expose internal reviewer notes, private storage keys or evidence URLs.

`verified_at` must remain `null` until successful verification occurs.

## 6. List Payment Submissions

`GET /api/v1/payments/{payment_id}/submissions/`

Returns submission history for the authenticated customer's own payment.

### Successful response

HTTP `200 OK`.

```json
{
  "count": 2,
  "results": [
    {
      "id": "72e5904b-cf1b-4a2e-bde8-b25d4c4d5c91",
      "status": "rejected",
      "submitted_at": "2026-11-01T13:55:00+05:30",
      "reviewed_at": "2026-11-01T14:00:00+05:30",
      "rejection_reason": "Please upload a clearer screenshot."
    },
    {
      "id": "db9c8f11-c03f-4a5a-9a91-991d8d52a004",
      "status": "pending_review",
      "submitted_at": "2026-11-01T14:05:00+05:30",
      "reviewed_at": null,
      "rejection_reason": null
    }
  ]
}
```

This example illustrates the case where a customer submits replacement evidence after rejection.

Requirements:

- Return only submissions belonging to the customer's payment.
- Preserve the history of rejected submissions.
- Expose customer-appropriate rejection reasons only.
- Do not expose internal review notes.
- Do not include public or guessable evidence URLs.
- Apply pagination if the submission history can grow beyond a reasonable response size.

## 7. Submit Payment Screenshot

`POST /api/v1/payments/{payment_id}/submissions/`

Uploads payment evidence after order creation.

### Authentication

Required.

### Content type

`multipart/form-data`

### Request fields

| Field | Type | Required | Rules |
|---|---|---|---|
| `screenshot` | File | Yes | Must be an approved image format and pass server-side validation |

The screenshot is mandatory for every submission. Do not accept an empty file or a request without the screenshot.

Do not accept `amount_due`, `currency`, `status`, `verified_by`, `verified_at` or `order_status` as mutable fields in this request.

### Example

```http
POST /api/v1/payments/2c914a64-8c9f-45a7-8bc2-0123456789ab/submissions/
Authorization: <configured authentication credentials>
Content-Type: multipart/form-data
```

Form field:

```text
screenshot: <image file>
```

### Server-side processing

1. Authenticate the customer.
2. Resolve the payment and verify ownership.
3. Confirm that the payment is eligible for a new evidence submission.
4. Reject submissions for a verified payment.
5. Validate file content, format, dimensions and size.
6. Generate a server-controlled storage name.
7. Store the evidence in private storage.
8. Create a new submission record.
9. Update payment status to `pending_verification`.
10. Create the corresponding status-history record if the payment status changes.
11. Commit the database changes safely.
12. Return the submission record and current payment status.

The implementation must coordinate database writes and storage operations so failed requests do not leave untracked files or misleading submission records.

### Successful response

HTTP `201 Created`.

```json
{
  "id": "72e5904b-cf1b-4a2e-bde8-b25d4c4d5c91",
  "payment_id": "2c914a64-8c9f-45a7-8bc2-0123456789ab",
  "status": "pending_review",
  "submitted_at": "2026-11-01T13:55:00+05:30",
  "payment_status": "pending_verification",
  "message": "Payment screenshot received and awaiting verification."
}
```

This response confirms receipt of evidence only. It must not state that payment was successful or that the order has been confirmed.

### Possible errors

- `400 Bad Request`: missing screenshot or invalid request.
- `401 Unauthorized`: authentication missing or invalid.
- `403 Forbidden`: the caller cannot submit evidence for this payment.
- `404 Not Found`: payment does not exist or is not accessible to the customer.
- `409 Conflict`: payment is verified or the current state does not permit submission.
- `413 Content Too Large`: upload exceeds configured size limits, if this response is used by the project's upload stack.
- `415 Unsupported Media Type`: unsupported file format.
- `429 Too Many Requests`: upload rate limit exceeded, if configured.
- `500 Internal Server Error`: unexpected failure, without internal diagnostics.

## 8. Retrieve One Submission

`GET /api/v1/payments/{payment_id}/submissions/{submission_id}/`

Returns the customer's own submission metadata and review result.

### Successful response

HTTP `200 OK`.

```json
{
  "id": "72e5904b-cf1b-4a2e-bde8-b25d4c4d5c91",
  "payment_id": "2c914a64-8c9f-45a7-8bc2-0123456789ab",
  "status": "rejected",
  "submitted_at": "2026-11-01T13:55:00+05:30",
  "reviewed_at": "2026-11-01T14:00:00+05:30",
  "rejection_reason": "Please upload a clearer screenshot."
}
```

The endpoint must verify that both the payment and submission belong to the authenticated customer.

Retrieving submission metadata does not automatically grant access to the original file. If customers are permitted to view their uploaded screenshot, provide a protected evidence-access mechanism rather than a public URL.

## 9. Staff: List Payments

`GET /api/v1/payments/staff/`

Returns a paginated list of payments for designated reviewers.

### Permissions

Require the appropriate payment-review permission.

### Suggested query parameters

| Parameter | Type | Purpose |
|---|---|---|
| `status` | String | Filter by payment status |
| `order_number` | String | Search by order reference |
| `created_after` | ISO 8601 datetime | Filter by creation time |
| `created_before` | ISO 8601 datetime | Filter by creation time |
| `submitted_after` | ISO 8601 datetime | Filter by evidence submission time |
| `submitted_before` | ISO 8601 datetime | Filter by evidence submission time |
| `page` | Integer | Page number |
| `page_size` | Integer | Page size, subject to the configured maximum |

Only explicitly supported filters should be accepted.

The response may include payment ID, order number, amount due, currency, payment status, latest submission status and relevant timestamps.

Do not return screenshot bytes or unprotected evidence URLs in list responses.

## 10. Staff: Retrieve Payment Details

`GET /api/v1/payments/staff/{payment_id}/`

Requires explicit payment-review permission.

The response should include:

- Payment ID and associated order reference.
- Customer identity needed for verification.
- Expected amount and currency.
- Payment status.
- Submission history summary.
- Verification actor and timestamp, if verified.
- Payment-status history.
- Relevant audit metadata.

Keep reviewer-only fields separate from customer serializers. Do not return raw model objects or unrestricted internal metadata.

## 11. Staff: List Payment Submissions

`GET /api/v1/payments/staff/{payment_id}/submissions/`

Returns the submission history for an authorized review workflow.

Each entry may contain:

- Submission identifier.
- Submission status.
- Submission timestamp.
- Review timestamp.
- Reviewer identity.
- Rejection reason.
- A protected evidence-access action.

The endpoint must preserve previous submissions. Replacing evidence must never overwrite the record of a rejected screenshot.

## 12. Staff: Review a Submission

`POST /api/v1/payments/staff/{payment_id}/submissions/{submission_id}/review/`

Accepts or rejects a screenshot submission. It does not, by itself, establish that a payment has been successfully verified.

### Permissions

Require the explicit payment-review permission.

### Request body — rejection

```json
{
  "decision": "reject",
  "reason": "The screenshot is unclear and the transaction details cannot be checked."
}
```

### Request body — acceptance for verification

```json
{
  "decision": "accept",
  "reason": "Evidence accepted for payment verification."
}
```

The `accept` decision means that the evidence is acceptable for the verification workflow. It must not automatically mark the payment verified unless the implementation explicitly combines the two decisions into one auditable verification operation. The recommended design keeps evidence review and successful payment verification distinct.

### Field rules

| Field | Type | Required | Rules |
|---|---|---|---|
| `decision` | String | Yes | `accept` or `reject` |
| `reason` | String | Required for rejection | Length-limited and appropriate for customer display where applicable |

The server derives the reviewer identity from the authenticated user. Do not accept `reviewed_by`, timestamps or arbitrary payment-status values from the request.

### Rejection behavior

When a submission is rejected:

- Mark that submission as `rejected`.
- Record the reviewer and review timestamp.
- Record the reason.
- Preserve the submission.
- Keep the payment unverified.
- Permit a new screenshot submission if the payment is eligible.
- Return the current payment state.

### Successful response

HTTP `200 OK`.

```json
{
  "payment_id": "2c914a64-8c9f-45a7-8bc2-0123456789ab",
  "submission_id": "72e5904b-cf1b-4a2e-bde8-b25d4c4d5c91",
  "decision": "reject",
  "submission_status": "rejected",
  "payment_status": "rejected",
  "reviewed_at": "2026-11-01T14:00:00+05:30"
}
```

The example illustrates rejection. A real response must reflect the state actually committed by the server.

## 13. Staff: Verify Payment

`POST /api/v1/payments/staff/{payment_id}/verify/`

Records a successful manual verification decision.

### Permissions

Require explicit payment-verification permission. A user who can merely view payment records must not automatically receive verification privileges.

### Request body

```json
{
  "submission_id": "db9c8f11-c03f-4a5a-9a91-991d8d52a004",
  "verified_amount": "1200.00",
  "reason": "Payment verified against the available transaction evidence."
}
```

Field rules:

| Field | Type | Required | Rules |
|---|---|---|---|
| `submission_id` | UUID or configured identifier | Yes | Must identify an eligible submission belonging to this payment |
| `verified_amount` | Decimal string | Yes | Must match the expected full amount under the approved verification policy |
| `reason` | String | Recommended | Audit explanation for the verification decision |

The server derives the reviewer from the authenticated user. It must not trust a client-supplied reviewer ID, verification timestamp or order status.

The `verified_amount` field records the reviewer's assertion; it is not independently authoritative proof that funds were received. The reviewer must use the approved business verification process.

### Verification preconditions

The service must establish that:

1. The payment exists.
2. The reviewer has explicit permission.
3. The payment has not already been verified.
4. The referenced submission belongs to the payment.
5. The submission is eligible for verification.
6. The expected payment amount and currency are valid.
7. The verified amount matches the full expected amount.
8. The payment/order state permits the transition.
9. The verification action has not already been processed.

If the amount does not match, the endpoint must reject the request or follow a separately approved exception workflow. It must not silently accept partial or excess payment.

### Successful response

HTTP `200 OK`.

```json
{
  "id": "2c914a64-8c9f-45a7-8bc2-0123456789ab",
  "status": "verified",
  "method": "upi_qr",
  "amount_due": "1200.00",
  "verified_amount": "1200.00",
  "currency": "INR",
  "verified_by": "staff-user-id",
  "verified_at": "2026-11-01T14:10:00+05:30",
  "order_confirmation": {
    "status": "processed"
  }
}
```

The `verified_by` value should follow the project's chosen identifier or serializer convention. Do not expose sensitive staff information.

`order_confirmation.status` is an integration result, not a new payment state. Use a truthful value reflecting whether the order transition succeeded, is pending retry/reconciliation, or failed. Do not report successful order confirmation before the orders service confirms it.

### Transaction and integration behavior

The service must:

- Lock the payment and relevant submission records where necessary.
- Validate the current state.
- Update the payment and status history atomically.
- Record the reviewer and timestamp.
- Trigger the order transition through the approved service boundary or reliable event mechanism.
- Make repeated requests idempotent.
- Detect and reconcile failures between payment verification and order confirmation.

Do not perform an external side effect before the payment verification transaction is safely committed unless the integration is explicitly designed to support it.

## 14. Staff: Access Evidence Securely

`GET /api/v1/payments/staff/{payment_id}/submissions/{submission_id}/evidence/`

Requires explicit permission to review payment evidence.

The endpoint must verify:

- The caller is authenticated.
- The caller has the appropriate permission.
- The submission belongs to the specified payment.
- The evidence exists in private storage.
- The evidence has not been made inaccessible under the applicable retention policy.

Possible implementations include a protected file-streaming response or a short-lived signed URL. The chosen mechanism must prevent public or indefinite access.

Do not return a permanent public URL. Do not expose raw filesystem paths or storage object keys.

## 15. Payment and Order State Independence

The payments API must not expose a generic update endpoint for payment or order status.

The intended lifecycle is:

```text
Payment: awaiting_payment
       |
       | Screenshot submitted
       v
Payment: pending_verification
       |
       +---------------------------+
       |                           |
       v                           v
Payment: rejected             Payment: verified
       |                           |
       | Replacement screenshot    | Trusted verification result
       v                           v
Payment: pending_verification  Orders service may confirm order
```

The actual state transition after a rejected submission must be explicit and tested.

Important rules:

- `verified` means the payment has passed the approved manual verification process.
- `confirmed` is an order status, not a payment status.
- A submission being accepted for review does not necessarily mean the payment is verified.
- The payment API must not mark an order confirmed through an unprotected field update.
- Customer cancellation is not supported.
- No payment expiry job is supported at launch.
- No refund endpoint is supported at launch.

## 16. Error Response Convention

Use the project's common exception and error-response format. The following is an illustrative format:

```json
{
  "error": {
    "code": "payment_evidence_invalid",
    "message": "The uploaded screenshot could not be accepted.",
    "details": {
      "screenshot": [
        "Upload an approved image format within the configured size limit."
      ]
    }
  }
}
```

Recommended error codes:

| Code | Meaning |
|---|---|
| `authentication_required` | Authentication is required |
| `payment_not_found` | Payment does not exist or is not accessible |
| `permission_denied` | Caller lacks the required permission |
| `payment_evidence_required` | Screenshot is missing |
| `payment_evidence_invalid` | Screenshot failed validation |
| `payment_already_verified` | Evidence cannot be submitted to an already verified payment |
| `submission_not_found` | Submission does not exist or is not accessible |
| `invalid_payment_transition` | Requested payment transition is not allowed |
| `verification_amount_mismatch` | Verified amount does not match the expected amount |
| `verification_conflict` | Payment state changed concurrently or the request conflicts with existing state |
| `storage_unavailable` | Evidence storage operation failed |
| `order_sync_pending` | Payment verification succeeded but order synchronization needs recovery |

Use consistent HTTP status codes for these errors. Do not reveal another customer's payment existence or internal storage details.

## 17. Security Requirements

- Authenticate all customer payment operations.
- Enforce payment ownership for every customer endpoint.
- Enforce explicit permissions for review, verification and evidence access.
- Validate uploaded file contents and size.
- Store screenshots privately.
- Generate server-controlled storage names.
- Do not expose raw storage paths.
- Never trust client-supplied payment amounts, status or reviewer identity.
- Keep verification and audit records immutable through normal customer operations.
- Rate-limit uploads and sensitive review endpoints where appropriate.
- Use HTTPS in production.
- Avoid logging screenshots, private evidence URLs, authentication tokens or secrets.
- Prevent public access to private storage objects.
- Ensure that payment verification cannot be triggered by an ordinary customer.
- Protect against concurrent verification and duplicate submissions.
- Do not implement payment verification using OCR or screenshot appearance alone as proof of funds received.

## 18. OpenAPI Documentation

Every implemented endpoint must be documented in the project's OpenAPI schema.

For each endpoint, specify:

- Authentication requirements.
- Required permissions.
- Request schema and content type.
- Response schema.
- Error codes and HTTP status codes.
- Ownership checks.
- Upload size and file-format constraints.
- Idempotency behavior.
- Payment/order integration behavior.
- Whether evidence URLs are available and under what access restrictions.

Use distinct customer and staff serializers. Do not expose all model fields by default.

The schema must not advertise refunds, cash on pickup, partial payments, automatic expiry or customer cancellation as supported functionality.

## 19. Testing Requirements

### Payment instructions and access

- Authenticated customer can view payment instructions for their own order.
- Customer cannot access another customer's payment.
- Expected amount comes from the trusted payment record.
- Currency is INR.
- The configured fixed QR asset is returned correctly.
- Private evidence URLs are not returned in payment-instructions responses.

### Screenshot submission

- Unauthenticated upload is rejected.
- Customer cannot upload evidence for another customer's payment.
- Missing screenshot is rejected.
- Invalid file content is rejected.
- Unsupported file types are rejected.
- Oversized files are rejected.
- Upload is stored privately.
- Successful upload creates a submission record.
- Payment becomes pending verification.
- Screenshot upload does not mark payment verified.
- Rejected submissions remain in history.
- Customer can resubmit after rejection.
- Verified payment cannot accept ordinary new evidence.
- Failed storage or database operations do not leave untracked evidence.

### Manual verification

- Only designated users with explicit verification permission can verify.
- Users without permission are denied.
- Verification requires an eligible submission.
- The verified amount must match the expected full amount.
- Reviewer identity and timestamp are recorded.
- Verification and payment history are updated atomically.
- Duplicate verification requests are safe.
- Invalid transitions are rejected.
- Rejected evidence does not confirm an order.
- Successful verification permits the appropriate order transition through the trusted integration.
- Order-sync failures are detectable and recoverable.

### State and integration

- Payment status remains separate from order status.
- Order creation and payment creation do not produce undetected partial state.
- Repeated checkout requests do not create duplicate payment records.
- Duplicate verification events do not create duplicate order transitions.
- Payment verification cannot be invoked by a customer-facing endpoint.
- No automatic expiry or refund workflow runs.

### Security and schema

- Customer endpoints enforce ownership.
- Staff endpoints enforce explicit permissions.
- Private evidence requires authorization.
- Error responses do not leak internal details.
- OpenAPI matches actual serializers and views.
- Disabled features are not documented as available endpoints.

## 20. Explicitly Undecided Policies

| Decision | Current position | Required action |
|---|---|---|
| Tax and final payable amount | Not configured in the Orders architecture | Define the tax/pricing policy before production checkout |
| QR configuration and replacement procedure | One fixed QR code is confirmed; configuration mechanism is not finalized | Select and document a controlled configuration process |
| Payee verification | Required before production use | Establish a procedure for verifying the QR code and payee |
| Repeated screenshot rejection | Resubmission is allowed; escalation is undecided | Define how repeated rejection is handled |
| Duplicate or overpayment handling | Not decided | Approve a manual exception procedure |
| Refunds | Not implemented at launch | Approve a policy before implementing refunds |
| Evidence retention period | No automatic deletion | Define formal retention and compliance requirements |
| Screenshot size and accepted formats | Must be configured | Establish limits and communicate them to the frontend |
| Reviewer role assignment | Explicit permission required | Decide which staff roles receive it |
| Reconciliation operations | Required for cross-app failures | Define monitoring and recovery procedures |

These unresolved decisions must remain visible. Do not invent tax rules, refund behavior, payment expiry or exception-handling policies.

## 21. Definition of Done

The Payments API is ready for production review when:

- Payment instructions use the configured fixed UPI QR code.
- Expected amount equals the valid full order total.
- Screenshot evidence is mandatory and submitted after order creation.
- Evidence is stored privately.
- Customers can resubmit evidence after rejection.
- Only explicitly authorized staff can verify payments.
- Verification records the responsible reviewer and timestamp.
- Screenshot submission never automatically marks a payment verified.
- Payment and order statuses remain separate.
- Successful verification can trigger order confirmation through a reliable integration.
- Retries cannot create duplicate payment records or duplicate order transitions.
- Payment and evidence history are retained without automatic expiry or deletion.
- Refund and customer-cancellation endpoints are absent.
- Ownership, storage access and permission checks are tested.
- OpenAPI documentation matches the implementation.
- The tax/pricing policy is configured before production checkout is enabled.
- No migrations or production-data changes have been performed without explicit approval.

**Architecture principle:** The Payments API records payment obligations, private evidence and authorized verification decisions. It does not create orders or independently control order fulfilment. A screenshot is evidence for review, not proof of successful payment.

