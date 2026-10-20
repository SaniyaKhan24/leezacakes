# Payments App — Architecture and Structure

**Project:** Leeza Cakes  
**Path:** `backend/docs/apps/payments_structure.md`  
**App:** `apps.payments`  
**API prefix:** `/api/v1/payments/`  
**Status:** Architecture specification  
**Currency:** INR only  
**Launch payment method:** UPI QR with manual verification  
**Fulfilment:** Customer pickup only

---

## 1. Purpose and Scope

The `payments` app owns payment records, UPI payment instructions, payment screenshot evidence, manual verification, payment status transitions and payment-related audit history.

Leeza Cakes will use one fixed UPI QR code at launch. Customers must pay the full exact order total and upload a payment screenshot after creating an order. A designated staff member or administrator with explicit payment-verification permission must verify the evidence manually.

The payment workflow is separate from the order lifecycle. A payment submission does not mean that money has been received, and uploading a screenshot does not confirm an order.

The app is responsible for:

- Maintaining payment records associated with orders.
- Providing the configured UPI QR code and payment instructions.
- Recording the expected payment amount and currency.
- Accepting mandatory screenshot evidence from the customer.
- Securely storing and serving payment evidence.
- Tracking payment submission attempts.
- Supporting customer resubmission after evidence rejection.
- Providing authorized staff with payment-review operations.
- Recording verification decisions and audit history.
- Preventing unauthorized or duplicate payment-state transitions.
- Exposing a safe payment summary to authorized customers and staff.
- Coordinating successful verification with the `orders` app.
- Supporting future payment extensions without implementing unused launch features.

The app does **not** own order creation, order lifecycle, cart management, product pricing, authentication or notification delivery.

## 2. Confirmed Business Rules

The following are confirmed launch requirements.

1. UPI QR is the only supported payment method.
2. Leeza Cakes uses one fixed UPI QR code for all orders.
3. Customers must pay the full exact order total. Partial payment and advance-payment flows are not supported at launch.
4. An order must exist before the customer uploads payment evidence.
5. A payment screenshot is mandatory for every payment submission.
6. A designated staff member or administrator with explicit payment-verification permission must verify evidence manually.
7. A screenshot alone never constitutes successful payment verification.
8. A rejected screenshot may be replaced by a new submission.
9. Payment records and payment status belong to `apps.payments`.
10. Order lifecycle status belongs to `apps.orders`.
11. Only successful manual payment verification may permit an order to transition to `confirmed`.
12. Customers cannot cancel orders.
13. Cash on pickup is not supported.
14. INR is the only supported currency.
15. Pending payment records do not expire automatically.
16. Refunds are not implemented at launch. Refund policy remains undecided.
17. Payment screenshots must be stored privately and must never be exposed through public or guessable URLs.
18. Customer access is restricted to their own payment records and evidence.
19. Staff verification operations require explicit permissions and audit records.
20. Payment creation and order creation must be coordinated to avoid duplicate or orphaned records.
21. The app must not automatically delete pending payments or historical payment records.
22. No migrations or production-data changes may be performed without explicit approval.

## 3. App Responsibilities and Boundaries

### 3.1 What payments owns

- Payment records.
- Expected payment amount and currency snapshots.
- Payment method and configured UPI QR instructions.
- Payment submission attempts.
- Screenshot evidence metadata and secure storage.
- Payment status and verification history.
- Staff verification decisions.
- Payment-specific permissions and audit events.
- Payment/order reconciliation data.
- Safe payment summaries for API responses.

### 3.2 What other apps own

| App | Responsibility |
|---|---|
| `accounts` | Authentication, user identity and account lifecycle |
| `orders` | Order creation, order snapshots, pickup scheduling and order lifecycle |
| `cart` | Mutable cart contents and cart ownership |
| `catalog` | Products, variants and catalogue prices |
| `customization` | Customization definitions and allowed choices |
| `notifications` | Email, SMS or other notification delivery |
| `common` | Shared exceptions, validation utilities and infrastructure |

The payments app must not calculate an order total independently from catalogue or order pricing rules. It records the expected amount supplied by the trusted order-creation workflow after server-side validation.

The payments app must not independently confirm an order by directly changing arbitrary order fields. Successful verification must be communicated through a defined service boundary or reliable integration mechanism.

## 4. Recommended Directory Structure

```text
backend/
└── apps/
    └── payments/
        ├── __init__.py
        ├── apps.py
        ├── admin.py
        ├── models/
        │   ├── __init__.py
        │   ├── payment.py
        │   ├── payment_submission.py
        │   └── payment_status_history.py
        ├── serializers/
        │   ├── __init__.py
        │   ├── payment.py
        │   ├── payment_submission.py
        │   └── staff.py
        ├── views/
        │   ├── __init__.py
        │   ├── customer.py
        │   ├── submission.py
        │   └── staff.py
        ├── services/
        │   ├── __init__.py
        │   ├── payment_creation.py
        │   ├── payment_submission.py
        │   ├── verification.py
        │   ├── status_transitions.py
        │   └── reconciliation.py
        ├── selectors/
        │   ├── __init__.py
        │   ├── customer_payments.py
        │   └── staff_payments.py
        ├── storage.py
        ├── permissions.py
        ├── exceptions.py
        ├── urls.py
        ├── tests/
        │   ├── __init__.py
        │   ├── test_payment_models.py
        │   ├── test_payment_creation.py
        │   ├── test_payment_submission.py
        │   ├── test_payment_permissions.py
        │   ├── test_payment_verification.py
        │   ├── test_payment_transitions.py
        │   ├── test_payment_storage.py
        │   ├── test_payment_idempotency.py
        │   └── test_payment_order_integration.py
        └── migrations/
            └── __init__.py
```

This is the target architecture, not confirmation that every file already exists. Follow the repository's established conventions and avoid creating duplicate modules if equivalent implementations already exist.

## 5. Data Model

### 5.1 Payment

**Module:** `apps/payments/models/payment.py`

The `Payment` model represents the payment obligation and its current processing state for an order.

Recommended fields:

| Field | Suggested type | Purpose |
|---|---|---|
| `id` | UUID primary key | Stable internal identifier |
| `order` | One-to-one relationship, where one payment per order is enforced | Related order |
| `user` | Foreign key to configured user model | Customer responsible for the payment |
| `method` | Choice field | `upi_qr` |
| `status` | Choice field | Current payment state |
| `amount_due` | Decimal | Full expected order amount |
| `currency` | Fixed-value choice | `INR` |
| `expected_amount_snapshot` | Decimal, if separately needed | Immutable expected amount at payment creation |
| `verified_amount` | Nullable Decimal | Amount established by the authorized verification process, if recorded |
| `verified_by` | Nullable foreign key to configured user model | Staff member who verified the payment |
| `verified_at` | Nullable DateTime | Successful verification timestamp |
| `created_at` | DateTime | Payment creation timestamp |
| `updated_at` | DateTime | Last update |

Implementation notes:

- Use the configured user model, not a hard-coded Django user class.
- Use a one-to-one order relationship if the launch rule is strictly one payment record per order.
- If multiple payment attempts or replacement transactions need separate payment records later, revisit the relationship before implementation. Do not add that complexity prematurely.
- The expected amount must come from the trusted checkout workflow.
- The expected amount and currency must not be editable by customers.
- Use `DecimalField` for monetary values.
- Currency must be INR at launch.
- Store staff verification attribution only after a successful authorized decision.
- Do not allow arbitrary updates to `status`, `verified_by` or `verified_at` through a generic model serializer.
- Avoid cascade deletion of payment records when an order or user is deleted. Preserve historical records and choose suitable protected, nullable or anonymization relationships.
- Payment evidence submission history belongs in a separate model so a rejected submission is not overwritten by a replacement.

The exact relationship design must be reconciled with the existing order schema before migrations are approved.

### 5.2 PaymentSubmission

**Module:** `apps/payments/models/payment_submission.py`

Each `PaymentSubmission` represents one customer upload of payment evidence.

A separate record is necessary because customers can resubmit a screenshot after rejection. Previous submissions must remain auditable.

Recommended fields:

| Field | Purpose |
|---|---|
| `id` | Stable identifier |
| `payment` | Parent payment foreign key |
| `submitted_by` | Customer who uploaded the evidence |
| `evidence_file` | Private storage reference |
| `original_filename` | Sanitized original filename, if needed |
| `content_type` | Validated content type |
| `file_size` | File size in bytes |
| `status` | Submission review state |
| `submitted_at` | Upload timestamp |
| `reviewed_by` | Authorized reviewer, nullable |
| `reviewed_at` | Review timestamp, nullable |
| `rejection_reason` | Required when rejected, subject to policy |
| `created_at` | Record creation timestamp |

Recommended submission states:

- `pending_review`
- `accepted`
- `rejected`

The exact enum names can follow repository conventions, but their meanings must remain distinct.

Requirements:

- Every submission must contain valid evidence.
- A rejected submission must remain in history.
- A replacement upload creates a new submission record.
- An accepted submission cannot be replaced through the ordinary customer upload endpoint.
- Once the payment is verified, additional submissions must be rejected unless an explicit exception workflow is approved.
- Only authorized staff can accept or reject a submission.
- A customer cannot submit evidence for another customer's payment.
- The current submission may be derived from the latest eligible submission rather than duplicated in multiple mutable fields.
- Do not store the actual image bytes directly in ordinary JSON fields or expose storage paths to clients.
- Never trust file extensions alone for content validation.

The payment record must make it possible to identify the submission that supported the successful verification decision.

### 5.3 PaymentStatusHistory

**Module:** `apps/payments/models/payment_status_history.py`

Records significant changes to payment status.

Recommended fields:

| Field | Purpose |
|---|---|
| `id` | Stable identifier |
| `payment` | Related payment |
| `from_status` | Previous payment status, nullable on creation |
| `to_status` | New payment status |
| `changed_by` | Authenticated actor, nullable for an authorized system action |
| `related_submission` | Relevant submission, nullable |
| `reason` | Optional reason for a transition |
| `metadata` | Restricted structured audit metadata |
| `created_at` | Transition timestamp |

Requirements:

- The initial payment-history entry must be created with the payment record.
- Every successful payment-status transition must produce a history entry.
- Status and history updates must be atomic.
- Record the staff actor for manual verification decisions.
- Keep rejection reasons and audit details appropriate for operational use.
- Do not place screenshot contents, credentials or unnecessary personal data in audit metadata.
- Do not expose unrestricted history mutation to customers.
- Retain history alongside the payment record.

Submission-review history must also be preserved. Do not overwrite a rejected submission's decision when a new submission is uploaded.

## 6. Payment Status Lifecycle

Payment status is independent of order status.

Recommended payment states:

| Status | Meaning |
|---|---|
| `awaiting_payment` | Payment record exists; evidence has not yet been submitted |
| `pending_verification` | A screenshot has been submitted and is awaiting authorized staff review |
| `verified` | Staff has successfully verified the payment |
| `rejected` | The current evidence or verification attempt was rejected |
| `failed` | A payment failure has been established by an approved workflow |

`failed` should only be used when its meaning and triggering conditions are explicitly defined. Do not use it as a generic substitute for a rejected screenshot.

### 6.1 Normal launch flow

```text
Order created
     |
     v
Payment: awaiting_payment
     |
     | Customer uploads screenshot
     v
Payment: pending_verification
     |
     | Authorized staff reviews evidence
     +--------------------------+
     |                          |
     v                          v
Payment: verified         Payment: rejected
     |                          |
     v                          | Customer submits replacement
Order may be confirmed          |
                                v
                        Payment: pending_verification
```

The exact internal implementation may represent a rejected payment as `rejected` until a new submission is received. The status-transition service must define how the payment returns to `pending_verification` when the customer uploads replacement evidence.

### 6.2 Transition rules

Implement payment transitions in `services/status_transitions.py`.

The service must:

- Define allowed source and destination statuses.
- Reject invalid transitions.
- Require explicit staff permissions for verification decisions.
- Record the reviewer and timestamps for successful verification.
- Record rejection decisions and associate them with the relevant submission.
- Ensure a verified payment cannot be accidentally reset by a normal screenshot upload.
- Prevent duplicate verification actions from generating inconsistent state.
- Lock the payment record where concurrent actions could conflict.
- Update payment state and history atomically.
- Coordinate order updates through the defined cross-app service boundary.

Only successful manual verification may permit the order to transition to `confirmed`.

A screenshot upload is a submission event, not a payment-success event.

## 7. Fixed UPI QR Configuration

The launch implementation uses one fixed UPI QR code.

The QR code should be managed through configuration or a controlled administrative configuration mechanism. Do not hard-code sensitive or environment-specific values throughout the codebase.

Recommended configuration:

- QR image or protected/static asset reference.
- Display name for the payee.
- Optional payment instructions.
- Optional support contact instructions, if approved.

The QR image may be served publicly if it contains only the intended payment details and has been approved for public display. This is different from private payment screenshots uploaded by customers.

Do not assume that the QR code itself proves a transaction was completed.

### Fixed versus dynamic amount

Because the launch uses one fixed QR code, the application must clearly display the exact order amount the customer must pay.

If the QR code is a static merchant QR without a prefilled transaction amount, the customer may need to enter the amount manually in their UPI application. The app must not claim that a fixed QR code automatically enforces the order amount.

If the QR asset or UPI instructions embed a fixed amount, verify that this is compatible with variable order totals before launch. A fixed QR code must not be misrepresented as a unique order-linked payment request.

The expected amount stored in the payment record remains authoritative for comparison during manual verification.

The exact QR configuration source, update procedure and payee-verification procedure must be documented before production launch.

## 8. Full-Amount Payment Policy

The customer must pay the full exact order total.

Requirements:

- No partial payments at launch.
- No advance-payment percentage at launch.
- No cash on pickup.
- No alternative payment methods at launch.
- Expected amount must match the finalized order payable amount.
- Currency must be INR.
- Client-supplied amounts must not be trusted.
- Payment evidence must be reviewed against the expected amount and the available transaction evidence.

The payments app does not own catalogue pricing or tax calculations. It receives the authoritative payable amount from the order-creation workflow.

**Tax policy remains undecided.** The order must not be submitted with an invented or misleading total. Checkout must remain disabled until the business approves a usable pricing and tax policy.

The payment model must preserve the expected amount snapshot for the lifetime of the payment record.

If a payment amount does not match the expected order total, the reviewer must not mark it verified without an explicitly approved exception procedure.

## 9. Screenshot Evidence and Secure Storage

Payment screenshots are private transaction evidence.

Use private object storage or an equivalently protected storage mechanism. Do not place customer screenshots in a public media directory.

### Upload requirements

- Accept screenshots only through authenticated endpoints.
- Require the uploader to own the related payment.
- Accept only approved image formats.
- Validate the actual file content, not only the extension or declared MIME type.
- Enforce configurable maximum file size and image dimensions.
- Generate storage names server-side.
- Sanitize any retained original filename.
- Prevent executable content from being served as an image.
- Store files outside executable application paths.
- Do not return raw storage keys or filesystem paths.
- Serve evidence through an authorized download/view operation or short-lived signed URL.
- Ensure private storage objects are not accessible without authorization.
- Consider malware scanning and image re-encoding as defense-in-depth where supported.
- Avoid logging file contents, private URLs or unnecessary customer information.

The maximum file size and allowed formats must be centralized in configuration and documented for the frontend.

### Evidence access

Customers may upload and view their own submission status. Whether they can retrieve the original uploaded image after submission should follow a deliberate privacy policy.

Authorized payment reviewers may access evidence required for verification.

Other customers, public visitors and staff without the payment-review permission must not access screenshots.

### Evidence retention

Do not automatically delete screenshots as part of pending-payment cleanup because no automatic payment expiry is supported.

The formal retention period, archival requirements and privacy obligations remain undecided. Until a policy is approved, the application must not silently implement automatic evidence deletion.

## 10. Customer Payment Workflow

### 10.1 Payment instructions

After an order is created, the customer should see the order's payment instructions.

The UI may display:

- Order number.
- Expected payment amount.
- Currency.
- The configured fixed UPI QR code.
- Approved payee/payment instructions.
- Current payment status.
- Screenshot-upload action.

The payment instructions must be generated from trusted payment and order records. The client must not be able to modify the expected amount.

### 10.2 Submit screenshot

The customer uploads a screenshot after order creation.

The server must verify:

1. The customer is authenticated.
2. The payment exists.
3. The payment belongs to the authenticated customer.
4. The payment is not already verified.
5. The payment is in a state that permits a new submission.
6. The uploaded file passes all security and validation checks.
7. The submission is recorded without overwriting prior submissions.

After a successful upload, the payment should enter or return to `pending_verification`, and a submission record should be created.

The response must confirm only that evidence was received, not that the payment succeeded.

### 10.3 Rejected screenshot

When authorized staff rejects a screenshot:

- Record the rejected submission.
- Record the reviewing staff member.
- Record the review timestamp.
- Record an appropriate rejection reason.
- Keep the payment unverified.
- Permit the customer to submit replacement evidence.
- Preserve the previous submission and its history.

The exact customer-visible rejection reasons and the rules for repeated rejection remain to be defined. Avoid exposing sensitive internal fraud-review notes.

### 10.4 Verified payment

When staff verifies the payment successfully:

- Record the verifying staff member and timestamp.
- Associate the successful decision with the relevant evidence submission.
- Update the payment and history atomically.
- Notify the order workflow through the supported service boundary.
- Permit the order to transition to `confirmed` only after the successful verification result is established.
- Prevent duplicate confirmation and duplicate side effects.

If the order update fails after payment verification, the system must detect and reconcile the inconsistent state rather than silently treating the operation as fully complete.

## 11. Manual Verification and Permissions

Payment verification is a privileged operation.

Define an explicit permission such as `payments.verify_payment` and apply it to the staff verification endpoints and service methods.

The permission should be granted only to designated staff or administrators who are authorized to verify payments.

Do not assume every authenticated staff member may verify payments.

Verification must require the reviewer to inspect the available evidence and make an explicit decision.

Recommended verification checks include:

- Expected order amount.
- Payment amount supported by the available evidence.
- Currency.
- Transaction/reference details where available.
- Payee information where available.
- Evidence consistency and duplicate indicators.

A screenshot may be fabricated or incomplete. The application must not claim that image processing or OCR establishes actual receipt of funds. Staff must use the business's approved verification method.

The following audit details should be recorded:

- Payment identifier.
- Submission identifier.
- Reviewer identity.
- Decision.
- Timestamp.
- Rejection reason when applicable.
- Relevant non-sensitive audit metadata.

The exact staff role assignment and any escalation procedure remain implementation and business-policy decisions.

## 12. Orders Integration

The orders app owns the order lifecycle; payments owns the payment lifecycle.

The two must communicate through a defined service boundary. Avoid circular imports and avoid having the payments app update arbitrary order model fields directly from a view.

### Order creation

The trusted order-creation workflow should create the payment record using:

- The order identifier.
- The authenticated customer.
- The validated full payable amount.
- Currency `INR`.
- Payment method `upi_qr`.
- Initial payment state `awaiting_payment`.

The payment record should be created as part of a coordinated order-creation workflow so a failed transaction cannot leave a successful order without its required payment record, or an orphaned payment record without an order.

If the models use separate database transactions or external services, implement explicit retry and reconciliation behavior.

### Successful verification

After successful manual verification, payments must emit or invoke a trusted verification result.

The orders app may then transition the order from `pending_payment_verification` to `confirmed`, provided the result is valid and the transition remains permitted.

Requirements:

- A customer cannot directly trigger this transition.
- A payment screenshot cannot trigger it automatically.
- Repeated verification events must be idempotent.
- The order must not be confirmed when payment verification is rejected.
- A verified payment must not be reset by a later screenshot upload.
- Order and payment states must remain separately auditable.

### Reconciliation

Implement `services/reconciliation.py` for detecting and resolving cases such as:

- Payment is verified but the order remains pending verification.
- An order exists without the expected payment record.
- Duplicate events or retries were received.
- A transition failed after the payment state changed.

Reconciliation must not silently fabricate a successful payment or override staff decisions. Recovery actions must be safe, auditable and repeatable.

## 13. Refunds and Exceptions

Refunds are explicitly **not implemented at launch**. The refund policy is undecided.

Do not add:

- Refund endpoints.
- Automatic refund workflows.
- Partial-refund models.
- Refund processing jobs.
- Customer-initiated cancellation-to-refund flows.

Do not implement a refund by changing a payment from `verified` back to `pending_verification`.

If a refund requirement is approved in the future, design a separate refund model and workflow with its own statuses, permissions, audit history and reconciliation behavior.

Customers cannot cancel orders. This does not establish a complete policy for staff-initiated exceptions, duplicate payments or accidental overpayments. Those cases must be handled only under an explicitly approved operational policy.

## 14. API Responsibilities

Detailed request/response schemas belong in `backend/docs/apps/payments_api.md`.

The target API should support the following capabilities, subject to the project's established URL conventions.

### Customer capabilities

- Retrieve payment instructions for an order owned by the authenticated customer.
- Retrieve the customer's own payment status.
- Submit mandatory screenshot evidence.
- View the status of the customer's own submissions.
- Submit replacement evidence after rejection, while the payment remains eligible for resubmission.

The API must not allow customers to change payment status, amount, verification result, reviewer identity or order status.

### Staff capabilities

- List and filter payments for authorized reviewers.
- Retrieve payment details and review history.
- Access private screenshot evidence through a protected operation.
- Accept or reject a submission.
- Record the verification decision and relevant audit details.

Staff verification endpoints must enforce explicit payment-verification permission.

### Not supported at launch

- Cash on pickup.
- Card payments.
- Payment gateways.
- Partial payments.
- Customer cancellation.
- Refunds.
- Automatic payment expiry.
- Automatic screenshot-based payment verification.

## 15. Transactions, Concurrency and Idempotency

Payment operations must be safe under retries and concurrent requests.

Required protections:

- Enforce the intended payment-to-order relationship at the database level.
- Prevent duplicate payment creation during checkout retries.
- Prevent multiple concurrent submissions from overwriting one another.
- Prevent duplicate verification actions from generating inconsistent states.
- Lock the payment or relevant submission record where concurrent review actions may conflict.
- Update payment status and history atomically.
- Preserve rejected submission history.
- Prevent an already verified payment from accepting ordinary replacement submissions.
- Make order-confirmation events idempotent.
- Coordinate database transactions with any storage operations that cannot participate in the database transaction.
- Clean up orphaned uploaded files through a safe compensating mechanism when database persistence fails.
- Ensure retrying an operation cannot create duplicate payment records or duplicate order confirmations.

Do not rely solely on frontend button disabling or request sequencing.

## 16. Django Admin

Django admin may provide authorized staff with:

- Payment search by order number or payment identifier.
- Filtering by payment status and submission date.
- Expected amount and currency.
- Submission history.
- Reviewer identity and timestamps.
- Payment-status history.
- Access to private evidence through the authorized storage mechanism.

Admin actions must use the same domain services and permission checks as the API.

Do not permit unrestricted direct editing of `status`, `verified_by`, `verified_at` or evidence-review outcomes.

Payment screenshots must not be exposed through an unprotected admin link or public media URL.

## 17. Testing Requirements

### Payment creation

- Payment is created for the correct order and authenticated customer.
- Expected amount matches the trusted order total.
- Currency is INR.
- Payment method is `upi_qr`.
- The initial status is `awaiting_payment`.
- Duplicate checkout retries do not create duplicate payment records.
- An order and its payment cannot become partially persisted without a detectable recovery path.

### Screenshot submissions

- Unauthenticated upload is rejected.
- A customer cannot submit evidence for another customer's payment.
- Screenshot evidence is mandatory.
- Invalid file types are rejected.
- Files exceeding configured limits are rejected.
- File content is validated independently of the filename.
- Uploaded evidence is private.
- Storage paths and private URLs are not exposed.
- A successful upload enters the appropriate verification state.
- Uploading a screenshot does not mark payment verified.
- A rejected submission remains in history.
- The customer can submit replacement evidence after rejection.
- A verified payment cannot accept ordinary new submissions.

### Manual verification

- Only designated users with explicit payment-verification permission can review evidence.
- Staff without the permission are denied.
- Verification records the reviewer and timestamp.
- Rejection records the relevant submission and reason.
- A payment cannot be verified through a customer-facing endpoint.
- Verification and payment history are updated atomically.
- Duplicate verification requests are safe.
- An invalid transition is rejected.
- A successful verification can trigger the appropriate order transition.
- A rejected verification does not confirm the order.

### Order integration

- Payment status and order status remain independent.
- An order starts in `pending_payment_verification`.
- The order is not confirmed before successful manual verification.
- Duplicate verification events do not duplicate order transitions.
- Failed cross-app operations can be detected and reconciled.
- Payment creation and order creation follow the intended transactional boundary.

### Retention and refunds

- Pending payments do not expire automatically.
- Historical payment records are not automatically deleted.
- Refund endpoints and workflows are not exposed at launch.
- Customers cannot cancel orders through the payments API.

### API and schema

- Customer endpoints enforce ownership.
- Staff endpoints enforce explicit permissions.
- OpenAPI documents all implemented endpoints and permissions.
- Error responses follow the project's common convention.
- No endpoint exposes private evidence through public URLs.

Tests must use isolated test data and mocked external dependencies where appropriate. Do not make live payments or access production evidence in routine tests.

## 18. Observability and Error Handling

Log meaningful payment events, including:

- Payment record creation.
- Screenshot submission success or failure.
- Verification decisions.
- Rejected submissions.
- Permission failures where operationally appropriate.
- Duplicate/idempotent requests.
- Order/payment synchronization failures.
- Reconciliation actions.

Use safe correlation identifiers, such as internal payment and order IDs.

Never log screenshot bytes, private storage URLs, authentication tokens, secrets or unnecessary customer data.

Errors returned to the client must be actionable without revealing private transaction evidence or internal infrastructure details.

A payment/order synchronization failure must be observable and recoverable. It must not be silently interpreted as successful end-to-end confirmation.

## 19. Implementation Order

Implement in this order:

1. Review the existing `orders` model and finalized orders architecture.
2. Confirm the payment-to-order relationship and payment-creation boundary.
3. Define the payment and submission models.
4. Define payment states and permitted transitions.
5. Configure the fixed UPI QR asset and approved payment instructions.
6. Implement secure private screenshot storage.
7. Implement customer submission and resubmission services.
8. Implement explicit payment-verification permissions.
9. Implement staff review and audit-history services.
10. Implement idempotent order/payment coordination.
11. Implement the trusted payment-verification-to-order-confirmation integration.
12. Implement reconciliation for inconsistent cross-app states.
13. Add customer and staff API endpoints.
14. Add OpenAPI documentation and comprehensive tests.
15. Verify storage permissions, access control, logging and production configuration.

Do not run migrations until the model design and cross-app relationships have been reviewed and explicitly approved. Never run migrations against production or modify production data without explicit approval.

## 20. Explicitly Undecided Policies

The following decisions remain open and must not be invented during implementation.

| Decision | Current position | Required action |
|---|---|---|
| Refund policy | Refunds are not implemented at launch | Approve a policy before adding refund functionality |
| QR asset configuration and replacement procedure | One fixed QR code is confirmed; configuration mechanism is not finalized | Choose and document a controlled configuration process |
| QR payee verification | Must be validated before production | Establish an approved verification procedure |
| Tax and final payable amount | Unconfigured in the orders architecture | Define the tax/pricing policy before enabling checkout |
| Rejected-evidence reason taxonomy | Resubmission is allowed; exact reason categories are undecided | Define customer-visible and internal reason handling |
| Repeated rejection handling | Not decided | Define the staff escalation process |
| Duplicate or overpayment handling | Not decided | Approve a staff procedure before automating exceptions |
| Payment-evidence retention period | No automatic deletion | Define formal retention and compliance requirements |
| Maximum screenshot size and accepted formats | Must be configured | Set centralized upload limits before launch |
| Staff role assignment | Explicit permission is required | Decide which staff roles receive it |
| Cross-app reconciliation operations | Required where inconsistency can occur | Define operational monitoring and recovery procedures |

These policies must remain explicit configuration or implementation gates. In particular, the payments app must not enable production checkout if the orders app cannot calculate a valid exact payable total.

## 21. Definition of Done

The payments app is ready for production review only when:

- Each eligible order has the intended payment record.
- The expected full order amount is recorded accurately in INR.
- The fixed UPI QR code and payment instructions are configured and verified.
- Screenshot evidence is mandatory for each submission.
- Evidence is stored privately and served only to authorized users.
- Customers can resubmit evidence after rejection.
- Only designated staff with explicit permission can verify payments.
- Successful verification records reviewer identity and audit history.
- Uploading evidence never automatically marks payment verified.
- Payment and order statuses remain separate.
- Only successful verification can permit order confirmation.
- Checkout retries cannot create duplicate payment records.
- Rejected submissions remain auditable.
- Pending payments and historical records are not automatically deleted.
- Refunds and customer cancellation are not exposed at launch.
- Cross-app failures are detectable and recoverable.
- Tests cover security, permissions, state transitions, idempotency, storage and order integration.
- OpenAPI documentation matches the implementation.
- No migrations or production-data changes have been performed without explicit approval.

**Architecture principle:** `payments` owns the payment record, private evidence and manual verification decision. `orders` owns the order and its fulfilment lifecycle. A payment screenshot is evidence to review, not proof of successful payment; only an authorized successful verification can permit order confirmation.