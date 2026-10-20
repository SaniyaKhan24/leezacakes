# Notifications App — Structure and Architecture

**Project:** Leeza Cakes  
**Backend:** Django + Django REST Framework  
**Document:** `backend/docs/apps/notifications_structure.md`  
**Status:** Architecture specification; implementation and provider configuration pending

---

## 1. Purpose

The `notifications` app is responsible for delivering transactional and marketing communications to Leeza Cakes customers and authorized staff.

It centralizes notification creation, message rendering, delivery scheduling, provider integration, retry handling, and minimal delivery history.

The app must support the launch requirements:

- Customer notifications through WhatsApp and an SMS integration, subject to provider feasibility and configuration.
- Transactional order and payment notifications.
- Promotional messages, including offers and announcements, with appropriate customer consent and opt-out handling.
- Staff notifications through both WhatsApp and email where those channels are configured.
- Asynchronous delivery using Celery.
- Minimal persisted delivery history rather than a comprehensive notification analytics system.

The app does **not** own order processing, payment verification, account authentication, cart management, or the business rules that determine when an event occurs.

## 2. Confirmed decisions

| Area | Decision |
|---|---|
| Customer launch channels | WhatsApp and SMS |
| Email delivery | Undecided; provider and activation pending |
| WhatsApp integration | Undecided; implementation provider and credentials pending |
| SMS integration | No third-party vendor selected; investigate a direct provider integration |
| Customer order/payment events | Seven specified events; see Section 5 |
| Staff alerts | Both WhatsApp and email, subject to configuration |
| Transactional notifications | Mandatory; customers cannot disable essential transactional messages through notification preferences |
| Marketing notifications | Supported, including offers; separate consent and opt-out rules required |
| Delivery architecture | Celery asynchronous tasks |
| Delivery history | Minimal operational history |
| Checkout and fulfillment | Authenticated orders, UPI QR payment, manual payment review, takeaway/pickup only |
| Migrations | Not authorized by this document |

A channel being selected for launch does not mean that its provider has been integrated, credentials configured, templates approved, or live delivery verified.

## 3. Scope and ownership

### 3.1 Responsibilities owned by `notifications`

The app owns:

- Notification event intake and dispatch.
- Mapping supported business events to notification types and recipients.
- Transactional and marketing message classification.
- Template selection and rendering.
- Provider-independent notification interfaces.
- WhatsApp and SMS delivery adapters.
- Email delivery adapter when a provider is selected.
- Celery tasks for asynchronous delivery and bounded retries.
- Idempotency and duplicate-delivery prevention where technically possible.
- Minimal delivery-attempt status and sanitized error information.
- Staff notification routing.
- Marketing consent checks and suppression rules.
- Operational logging and delivery failure handling.

### 3.2 Responsibilities explicitly outside the app

The app must not:

- Create, modify, or cancel orders.
- Decide whether an order is confirmed or ready for pickup.
- Verify payment screenshots or mark payments as paid.
- Calculate order totals, taxes, product prices, or pickup availability.
- Authenticate users or implement account registration.
- Own email-verification or password-reset tokens.
- Own the cart or convert a cart into an order.
- Store payment credentials or sensitive payment information.
- Expose private payment evidence through notification messages.
- Treat successful message delivery as proof that an order or payment operation succeeded.

The owning domain app remains the source of truth. Notifications communicate an already-authoritative event; they do not create that event.

## 4. App boundaries and dependencies

### 4.1 `accounts`

`accounts` owns user identity, contact information, authentication, email verification, password-reset workflows, and account security rules.

`notifications` owns the delivery mechanism used by those workflows.

Expected integration:

- `accounts` validates and issues verification or password-reset tokens.
- `accounts` invokes the notification service with the appropriate recipient, template identifier, and short-lived action link or token payload.
- `notifications` renders and delivers the message through an enabled channel.
- `notifications` does not generate, validate, or consume authentication tokens.
- Security-sensitive values must never appear in routine logs.

Until email delivery is selected, email-dependent verification and password-reset delivery remain an implementation dependency. An approved alternative must be defined before those workflows are relied upon in production.

### 4.2 `orders`

`orders` owns order creation, order status, pickup scheduling, order items, and historical order snapshots.

The initial order status is `pending_payment_verification`. Order notifications must reflect the actual persisted order status.

`notifications` may communicate the following order events:

- Order created.
- Order confirmed.
- Order preparing.
- Order ready for pickup.
- Order completed.

The app must not infer that an order is confirmed merely because a customer created an order or submitted a payment screenshot.

### 4.3 `payments`

`payments` owns payment records, uploaded payment evidence, manual staff review, and payment verification status.

Leeza Cakes initially accepts UPI QR payments, with staff manually reviewing submitted payment screenshots.

`notifications` may communicate:

- Payment verified.
- Payment rejected.

A notification must only be queued after the corresponding payment state has been persisted successfully. Rejection messages must not expose internal reviewer notes, private evidence URLs, or unnecessary payment information.

Payment status and order status remain separate. Payment verification may cause an order transition through the owning domain workflow, but the notification app must not perform that transition itself.

### 4.4 `cart`

`cart` owns cart items, variant selection, customization selections, and cart validation.

`notifications` does not send routine cart notifications at launch and must not create orders from carts.

### 4.5 `common`

`common` may provide shared infrastructure such as:

- Standardized API exceptions.
- Correlation identifiers.
- Shared validation utilities.
- Common logging conventions.
- Health and readiness infrastructure.

Notification-specific provider errors, delivery states, message templates, and dispatch logic remain in `notifications`.

### 4.6 Dependency direction

Domain apps should invoke a stable notification service or publish a domain event. They should not import provider-specific WhatsApp, SMS, or email client implementations.

Recommended logical flow:

`orders/payments/accounts` → notification service or domain event → database transaction commits → Celery task → notification dispatcher → channel adapter → external delivery interface

The notification app must not create circular imports between domain apps.

## 5. Customer transactional events

The following seven event types are in scope for launch.

| Event key | Meaning | Source of truth |
|---|---|---|
| `order_created` | An order was successfully created | `orders` |
| `payment_verified` | Staff successfully verified the payment | `payments` |
| `order_confirmed` | The order entered its confirmed state | `orders` |
| `preparing` | Preparation began | `orders` |
| `ready` | The order is ready for pickup | `orders` |
| `completed` | The order was completed or collected | `orders` |
| `payment_rejected` | Staff rejected a payment submission or payment review | `payments` |

### 5.1 Event semantics

Each event must correspond to an actual, persisted business event. Notifications must not be triggered merely because a frontend sends a request or displays a success message.

For example:

- `order_created` is emitted after successful order creation.
- `payment_verified` is emitted after successful payment verification.
- `order_confirmed` is emitted only when the order enters the confirmed state.
- `payment_rejected` must distinguish rejection of a submitted payment screenshot from any broader payment-state change where the distinction matters to the message.

A payment being verified and an order being confirmed are separate events. The owning domain workflow determines whether and when both occur.

### 5.2 Message content

Messages should contain only the information needed by the recipient.

Where appropriate, customer-facing messages may include:

- Order number.
- Concise order status.
- Pickup instructions.
- A link to the authenticated order page.
- A brief next step when payment evidence is rejected.

Do not include full addresses, authentication tokens, payment screenshots, internal staff notes, or unnecessary customer data in message content.

The exact wording, template identifiers, supported languages, and provider template approvals remain implementation decisions.

## 6. Marketing notifications and customer preferences

Transactional and marketing messages must be treated as separate categories.

### 6.1 Transactional messages

Transactional messages relate to an account, an order, a payment, or fulfillment.

The confirmed policy is `transactional_mandatory`: customers cannot disable essential transactional notifications through ordinary marketing preferences.

This does not mean every channel must always be used. Delivery is still subject to valid contact details, channel availability, technical failures, and applicable legal requirements.

### 6.2 Marketing messages

Marketing notifications may include:

- Offers and discounts.
- Seasonal cake promotions.
- New product announcements.
- Festival campaigns.
- Other promotional announcements approved by Leeza Cakes.

Marketing messages must be subject to a separate consent and opt-out mechanism. A customer accepting transactional notifications must not automatically be treated as consenting to promotional messaging.

The implementation must:

- Record marketing consent separately from transactional delivery.
- Check consent immediately before dispatch.
- Honor opt-outs and suppression records.
- Avoid sending promotional messages when consent is absent or invalid.
- Preserve enough audit information to establish the customer's current and relevant historical consent state.
- Avoid treating an existing order or account as automatic marketing consent.

Applicable Indian messaging, privacy, telecom, and platform requirements must be reviewed before enabling promotional campaigns. In particular, WhatsApp and SMS may have channel-specific consent, template, sender, registration, or opt-out requirements.

### 6.3 Preferences data model

A future-compatible preference model should support channel-level consent rather than a single global marketing toggle.

Suggested logical fields:

- `user`: relationship to the customer, with an appropriate uniqueness constraint.
- `marketing_whatsapp_enabled`: whether WhatsApp marketing is permitted.
- `marketing_sms_enabled`: whether SMS marketing is permitted.
- `marketing_email_enabled`: whether email marketing is permitted, when email is implemented.
- `marketing_consent_recorded_at`: timestamp for consent evidence where appropriate.
- `marketing_consent_source`: source of consent, such as checkout, account settings, or an explicit campaign opt-in.
- `updated_at`: last modification timestamp.

The final implementation must define how withdrawal, consent history, and evidence are recorded. A single current-state row may be sufficient for preference checks but may not, by itself, be sufficient as a complete consent audit trail.

Do not add a preference model for every possible future campaign feature. Implement only what is needed for the initial consent workflow and channel-level suppression.

## 7. Staff notifications

Staff alerts are required through both WhatsApp and email, subject to configuration.

Potential staff events include:

- New order awaiting payment verification.
- New payment submission requiring review.
- Payment rejection or review completion where operationally useful.
- Other explicitly approved operational events.

These are staff-facing events, not additional customer transactional event keys.

### 7.1 Recipient management

Staff recipients must be configured through an explicit, access-controlled mechanism.

Do not send internal alerts to every registered customer or assume every Django staff account has a valid WhatsApp number or email address.

The implementation should support:

- An explicit staff recipient list or a controlled staff-recipient configuration.
- Separate channel enablement for staff.
- Validation of recipient contact details.
- Safe handling of disabled or missing channels.

The final recipient configuration mechanism remains undecided.

### 7.2 Staff message content

Staff alerts may include an order number, the required action, and a link to the protected staff dashboard.

Do not include customer payment screenshots or unrestricted payment-evidence URLs in WhatsApp or email alerts. Staff should access evidence through the authorized application interface.

## 8. Background delivery architecture

Celery is the selected background-delivery architecture.

However, **takeaway-only operations do not eliminate the need for background delivery**. WhatsApp, SMS, and email are external delivery operations that can be slow or temporarily unavailable regardless of whether an order is delivered or collected.

Celery allows order and payment requests to finish without waiting for an external messaging service.

### 8.1 Proposed flow

1. A domain operation succeeds.
2. The owning app persists the order, payment, or account state.
3. After the database transaction commits, a notification event is dispatched or made available to a worker.
4. A Celery task resolves the notification type, recipient, channel, template, and eligibility rules.
5. The selected provider adapter sends the message.
6. The task records a minimal delivery outcome.
7. Transient failures may be retried according to a bounded retry policy.

### 8.2 Transaction safety

Do not enqueue a notification before the associated business transaction has committed.

Use Django's `transaction.on_commit()` as a minimum safeguard when dispatching a Celery task after a transaction.

For events that must not be lost if the application process stops between commit and queue publication, consider a transactional outbox pattern. An outbox record is committed in the same transaction as the business change and published to Celery by a separate worker.

**Recommendation:** Begin with `transaction.on_commit()` if the launch risk is acceptable and add a durable outbox if reliable event recovery is required. The production reliability requirement must be decided before treating queued notifications as guaranteed delivery.

A Celery task being enqueued does not guarantee that a message was sent or delivered.

### 8.3 Celery infrastructure

The implementation requires:

- Celery configuration in the Django project.
- A configured message broker.
- Worker process deployment.
- Task retry and timeout settings.
- Structured, sanitized task logging.
- Monitoring for repeated task failures.
- A documented way to operate workers in development and production.

Redis is a possible broker, but its use must not be assumed solely because Celery has been selected. The actual broker configuration must match the deployment environment.

No notification task should block the order or payment request while waiting for an external provider response.

## 9. Provider abstraction and channel selection

Provider selection must remain separate from business-event handling.

### 9.1 WhatsApp

The implementation must use a supported WhatsApp Business integration.

The specific provider, account setup, credentials, approved message templates, webhook configuration, and production activation remain undecided.

The adapter should expose a provider-independent interface such as:

- `send_transactional_message(...)`
- `send_marketing_message(...)`
- `get_provider_message_id(...)`, where available
- `normalize_provider_error(...)`

The exact method signatures should be finalized during implementation.

The adapter must handle provider-specific requirements without leaking provider details into `orders`, `payments`, or `accounts`.

Do not assume that a personal WhatsApp account or ordinary WhatsApp application can be used as a supported server-side messaging API.

### 9.2 SMS

The requirement is to avoid choosing a third-party SMS vendor if a direct Django integration is possible.

Django does not independently deliver SMS over the cellular network. A direct integration is possible only when a telecom or SMS service provider exposes a supported interface that the application can access.

Before implementing SMS, investigate whether Leeza Cakes has access to a provider-managed HTTP API, SMPP interface, or another authorized delivery interface.

The implementation must not:

- Attempt to send SMS directly through a customer's SIM or ordinary mobile messaging application from the Django server.
- Depend on unofficial gateway workarounds.
- Hard-code a vendor into business logic.
- Treat a local API response as proof of handset delivery.

Use an adapter boundary so the provider can be changed later.

SMS is currently off as a delivery capability until a compliant and technically supported integration is selected and configured. The architecture can include the adapter interface without enabling actual SMS dispatch.

If SMS is intended for OTP or account-security messages, that use case must be explicitly prioritized and designed with rate limiting, short token lifetimes, abuse protection, and the applicable telecom requirements. SMS OTP delivery is not automatically enabled by the current notification-channel decision.

### 9.3 Email

Email delivery remains undecided.

The architecture should permit an email adapter without requiring a provider-specific dependency in domain apps.

Before enabling email, decide the provider, sender identity, credentials, delivery monitoring, and whether email is used for account verification, password resets, staff alerts, or marketing.

Staff alerts require both WhatsApp and email, but delivery through either channel is only operational after that channel has been configured.

### 9.4 Provider configuration

Provider credentials must come from environment variables or the approved secrets-management system.

Do not commit API tokens, passwords, signing secrets, private keys, or provider credentials to source control.

Use explicit configuration to enable or disable each channel. Missing credentials should produce a clear configuration error, not silent message loss or fabricated success.

## 10. Recommended application structure

The following is the proposed logical layout. Exact module boundaries may be adjusted to match the existing repository, but the ownership boundaries should remain stable.

```text
backend/
└── apps/
    └── notifications/
        ├── __init__.py
        ├── apps.py
        ├── admin.py
        ├── models.py
        ├── tasks.py
        ├── urls.py
        ├── views.py
        ├── serializers.py
        ├── permissions.py
        ├── selectors.py
        ├── services/
        │   ├── __init__.py
        │   ├── dispatcher.py
        │   ├── event_handlers.py
        │   ├── preferences.py
        │   ├── recipients.py
        │   ├── templates.py
        │   └── idempotency.py
        ├── providers/
        │   ├── __init__.py
        │   ├── base.py
        │   ├── whatsapp.py
        │   ├── sms.py
        │   └── email.py
        ├── templates/
        │   └── notifications/
        │       ├── whatsapp/
        │       ├── sms/
        │       └── email/
        ├── tests/
        │   ├── __init__.py
        │   ├── test_models.py
        │   ├── test_preferences.py
        │   ├── test_dispatcher.py
        │   ├── test_tasks.py
        │   ├── test_providers.py
        │   └── test_permissions.py
        └── migrations/
```

This is a proposed structure, not a claim that these files already exist. Do not create unnecessary modules or directories solely to match the diagram.

### 10.1 Module responsibilities

- `models.py`: minimal notification records and channel-specific preferences, if implemented.
- `tasks.py`: Celery task entry points and retry configuration.
- `services/dispatcher.py`: central dispatch orchestration.
- `services/event_handlers.py`: mapping known business events to notification definitions.
- `services/preferences.py`: consent, channel preference, and suppression checks.
- `services/recipients.py`: safe recipient resolution.
- `services/templates.py`: template selection and rendering.
- `services/idempotency.py`: duplicate-event and duplicate-task protection.
- `providers/base.py`: provider interface and normalized outcomes.
- `providers/whatsapp.py`: WhatsApp adapter.
- `providers/sms.py`: SMS adapter boundary; delivery disabled until configured.
- `providers/email.py`: email adapter boundary; provider pending.
- `serializers.py` and `views.py`: only the API functionality required for customer preferences or authorized operational access.
- `permissions.py`: authorization for staff-only endpoints.
- `selectors.py`: query helpers for minimal notification history and operational views.
- `admin.py`: controlled administrative access to relevant records.

Avoid putting business-state transitions or payment verification logic in `event_handlers.py`.

## 11. Data model recommendations

Keep the launch data model small. Delivery attempts, customer preferences, and marketing consent have different purposes and should not be conflated.

### 11.1 `Notification`

An optional minimal record representing a notification intent.

Suggested fields:

- `id`: primary key.
- `event_key`: stable identifier such as `order_created`.
- `category`: `transactional` or `marketing`.
- `recipient_user`: nullable user reference where appropriate.
- `channel`: `whatsapp`, `sms`, or `email`.
- `status`: a normalized internal status.
- `deduplication_key`: stable key used to prevent duplicate processing.
- `created_at`: creation timestamp.
- `updated_at`: last state-change timestamp.

Do not store complete sensitive message payloads by default. Store only the minimum information needed to dispatch and troubleshoot a notification.

If the initial implementation can reliably operate with a smaller record model, do not add a full notification entity solely for architectural completeness.

### 11.2 Minimal delivery history

Delivery history should provide enough information to diagnose failures without becoming a full analytics or audit platform.

Possible fields:

- `notification`: optional reference to the notification intent.
- `channel`: attempted channel.
- `status`: `queued`, `sent`, `failed`, or another explicitly defined normalized state.
- `provider_message_id`: nullable external identifier.
- `attempt_count`: number of attempts.
- `last_attempt_at`: most recent attempt timestamp.
- `error_code`: sanitized provider or internal error code.
- `created_at` and `updated_at`.

Do not store full provider responses, authentication headers, raw secrets, OTP values, password-reset tokens, or unrestricted message payloads.

A provider returning an accepted response should be represented as accepted or sent according to the adapter's documented semantics. Do not label a message as delivered unless the provider provides a meaningful delivery confirmation.

A separate attempt-history table is not mandatory for launch. Add one only if the operational need to preserve every attempt outweighs the additional complexity.

### 11.3 Customer preferences and consent

Use a separate preference or consent model for marketing eligibility.

Transactional delivery must not be disabled by a marketing opt-out. Marketing delivery must not be permitted merely because transactional notifications are mandatory.

Where marketing consent must be auditable, record the consent source and relevant timestamps. Define the retention and withdrawal behavior before enabling marketing campaigns.

### 11.4 Template storage

Do not introduce a database-backed template editor unless staff need to modify templates without a code deployment.

A small set of version-controlled templates is sufficient for launch, provided provider-specific approved templates are kept synchronized with the code and deployment configuration.

Templates must be rendered with safe escaping appropriate to their output format. Dynamic values must not be interpreted as executable template source.

### 11.5 Database constraints and indexes

Where a persisted model is implemented, consider:

- An index on creation time and status for operational queries.
- An index on event key and creation time.
- A uniqueness constraint for an applicable deduplication key.
- A uniqueness constraint for the customer preference record, if the design uses one row per user.
- Appropriate indexes for staff queue queries.

Constraints must match the final schema. Do not invent a uniqueness rule that prevents legitimate repeated events, such as separate promotional campaigns or a new payment submission after a prior rejection.

## 12. Notification dispatch service

Domain apps should call a stable service interface rather than interact with channel providers directly.

Illustrative interface:

```python
dispatch_notification(
    event_key="order_created",
    recipient=customer,
    context={
        "order_number": order.order_number,
    },
    category="transactional",
    deduplication_key=f"order:{order.pk}:created",
)
```

This example describes an interface, not an existing function.

The actual implementation must define the required context schema for each event and reject unsupported event keys or missing required values.

The dispatcher should:

1. Validate the event key and category.
2. Resolve the intended recipient.
3. Determine enabled channels.
4. Apply the appropriate preference and consent rules.
5. Render the appropriate message.
6. Apply idempotency protection.
7. Enqueue delivery work through Celery.
8. Record the minimal operational outcome.

Marketing dispatch must require explicit eligibility. Transactional dispatch must use an allowlist of supported event keys and must not be used as a workaround for marketing consent.

## 13. Idempotency, retries, and failure handling

### 13.1 Idempotency

Duplicate events can occur because of task retries, repeated requests, webhook retries, or concurrent workers.

The system should derive a stable deduplication key from the source event and notification purpose.

Examples:

- Order creation notification: order identifier + event key.
- Payment verification notification: payment identifier + verification event identifier.
- Payment rejection notification: payment submission or review identifier + rejection event key.
- Marketing message: campaign identifier + recipient identifier + channel.

A payment may be rejected and subsequently resubmitted. Each distinct submission or review outcome must be eligible for its own notification.

A uniqueness constraint should protect the persisted deduplication key where the data model supports it.

### 13.2 Retries

Retry only failures that are plausibly transient, such as temporary network errors, provider rate limits, or transient service unavailability.

Do not retry indefinitely. Configure:

- A maximum attempt count.
- Exponential backoff or an equivalent bounded strategy.
- Provider-specific timeout limits.
- Handling for permanent errors, invalid recipients, rejected templates, and disabled channels.
- Monitoring or an operational queue for exhausted tasks.

Respect provider retry guidance and rate limits.

### 13.3 Duplicate external sends

Database idempotency cannot guarantee that a recipient never receives duplicates if the provider accepts a message but the application times out before recording the response.

Where available, use provider-supported idempotency keys or message-status reconciliation. Otherwise, document this limitation and keep retries bounded.

### 13.4 Failure isolation

Notification failure must not reverse a successfully committed order or payment state.

A failed notification must never change an order from `confirmed` to `pending_payment_verification`, mark a payment as rejected, or otherwise alter the owning app's business state.

## 14. API surface

The notifications app does not need a public API merely because it exists as a Django app.

The preferred launch design is for domain apps to invoke an internal service or publish events. Only expose customer preference endpoints or staff operational endpoints when a real frontend requirement exists.

Potential future endpoints include:

- `GET /api/v1/notifications/preferences/`
- `PATCH /api/v1/notifications/preferences/`
- `GET /api/v1/notifications/history/` (optional, authenticated customer access)
- Staff-only operational history or retry endpoints, if needed.

These are proposed endpoints, not a requirement to implement all of them.

Any customer-facing preference API must allow users to manage marketing preferences without exposing other customers' records or enabling them to disable mandatory transactional messages.

Staff operational endpoints must require explicit authorization. They must not expose secrets, raw provider payloads, or sensitive account tokens.

Do not add a public endpoint that lets an unauthenticated client submit arbitrary event keys or send arbitrary messages through the configured providers.

## 15. Security and privacy

Implementation requirements:

- Keep provider credentials in environment variables or approved secret storage.
- Never log access tokens, API keys, OTP values, password-reset tokens, or full authentication links.
- Validate recipients and message context.
- Apply rate limiting to any endpoint that can trigger a message, especially account-security workflows.
- Prevent arbitrary recipient injection.
- Escape dynamic template values.
- Limit access to notification history.
- Sanitize error messages before persisting them.
- Keep marketing consent separate from authentication and transactional status.
- Respect opt-outs and provider-level suppression.
- Verify signatures for any provider webhook used to receive status updates.
- Make webhook processing idempotent.
- Avoid exposing payment evidence in messages.
- Restrict staff recipient configuration and operational actions.
- Establish retention rules for contact data, consent evidence, and delivery history.

OTP and password-reset messages should be treated as security-sensitive. If implemented through this app, only the token or link produced by `accounts` may be used, and it must retain the expiry and validation behavior defined by `accounts`.

## 16. Configuration and deployment

Configuration should be channel-specific and fail clearly when an enabled channel is incomplete.

Suggested logical configuration groups:

- `CELERY_BROKER_URL`
- `NOTIFICATIONS_WHATSAPP_ENABLED`
- WhatsApp provider credentials and configuration.
- `NOTIFICATIONS_SMS_ENABLED`
- SMS interface credentials and configuration, once selected.
- `NOTIFICATIONS_EMAIL_ENABLED`
- Email provider and sender configuration, once selected.
- Staff recipient configuration.
- Per-channel timeout, retry, and rate-limit settings.

These are proposed configuration names; they must be aligned with the project's existing settings conventions before implementation.

Never commit real credential values to the repository. Keep local secrets in the approved local environment configuration and configure production secrets through the deployment platform.

Production deployment must include the Celery worker and configured broker if asynchronous delivery is enabled. Running Django's web process alone is not sufficient for queued tasks to execute.

Channel enablement must be explicit. A missing provider credential must not result in a false success status or silent fallback to an unsupported channel.

## 17. Testing requirements

Tests must not send real WhatsApp messages, SMS messages, or emails.

Use mocked provider adapters and an eager or test-specific Celery configuration where appropriate.

### 17.1 Event mapping

Verify that each of the seven confirmed customer events maps to the intended notification definition.

Verify that:

- Order creation does not imply payment verification.
- Payment verification does not automatically mean that an order-confirmed notification is valid.
- Order confirmation is based on the actual order state.
- Payment rejection uses the relevant review or submission event.
- Unsupported event keys are rejected.

### 17.2 Preferences and consent

Test that:

- Essential transactional notifications are not disabled by a marketing opt-out.
- Marketing notifications are suppressed without valid consent.
- WhatsApp marketing and SMS marketing preferences are checked independently.
- Opt-outs take effect before dispatch.
- Disabled channels do not accidentally invoke a provider.
- Staff notifications use only configured staff recipients.

### 17.3 Celery and transaction safety

Test that:

- Tasks are queued after transaction commit.
- A rolled-back transaction does not send a notification.
- Transient failures trigger only bounded retries.
- Permanent provider failures do not retry indefinitely.
- Duplicate events are deduplicated.
- A notification failure does not alter an order or payment state.
- A task does not report delivery success when the provider fails.

### 17.4 Provider adapters

Test normalized provider responses, timeouts, rate limits, invalid recipients, missing credentials, malformed responses, and provider rejection.

Tests must run without real provider credentials.

### 17.5 Security

Test that:

- Customer APIs cannot access another customer's notification history or preferences.
- Staff-only operations reject unauthorized users.
- Sensitive values are not written to application logs.
- Provider webhook signatures are validated where applicable.
- Untrusted input cannot choose arbitrary recipients or message templates.

### 17.6 Integration tests

Verify the interactions among `accounts`, `orders`, `payments`, `notifications`, and Celery using test doubles or a dedicated test environment.

Do not run tests that send messages to real recipients or mutate production data.

## 18. Implementation sequence

Recommended order:

1. Inspect the existing Django app, settings, dependencies, and Celery setup.
2. Confirm the notification service interface and the exact seven customer event contracts.
3. Define transactional versus marketing categories and the consent behavior.
4. Implement the provider-independent dispatcher and mocked adapter interface.
5. Configure Celery tasks and post-commit dispatch.
6. Implement minimal delivery history and deduplication.
7. Implement customer marketing preferences and suppression rules.
8. Implement the WhatsApp adapter after the provider is selected.
9. Investigate the supported SMS integration and implement its adapter only after the interface is confirmed.
10. Add the email adapter and staff email delivery when the provider is selected.
11. Connect domain events from `accounts`, `orders`, and `payments`.
12. Add and run automated tests in the approved development/test environment.
13. Configure worker deployment, secrets, monitoring, and provider templates.
14. Conduct end-to-end verification with approved test recipients before enabling production delivery.

Do not enable marketing campaigns before consent capture, suppression, and opt-out handling have been implemented and tested.

## 19. Explicitly undecided policies and blockers

The following decisions are intentionally not invented by this document.

| Item | Current state | Required before |
|---|---|---|
| WhatsApp provider | Undecided | WhatsApp implementation and live delivery |
| WhatsApp business account and approved templates | Unverified | Production WhatsApp messaging |
| SMS provider or direct interface | Undecided; SMS off | Any live SMS delivery |
| SMS OTP use case | Not confirmed | Account-security SMS implementation |
| Email provider | Undecided | Email delivery |
| Email account verification/password-reset strategy | Depends on account workflow and email availability | Production account lifecycle |
| Marketing consent capture flow | Not finalized | Promotional messaging |
| Marketing opt-out UX and processing | Not finalized | Promotional messaging |
| Staff recipient configuration | Not finalized | Operational alerts |
| Exact customer message copy and languages | Not finalized | Template approval and launch |
| Celery broker and deployment configuration | Must be verified | Asynchronous production delivery |
| Delivery retention period | Not finalized | Production data-retention policy |
| Delivery guarantee and outbox requirement | Not finalized | Production reliability sign-off |
| SMS and marketing regulatory requirements | Must be reviewed against the selected integration and use case | Live SMS or marketing delivery |

Takeaway-only operations do not remove these requirements. The app still needs reliable asynchronous delivery, channel configuration, consent handling, and correct event semantics.

## 20. Acceptance criteria

The notifications app is ready for launch when:

- Its boundaries with accounts, orders, payments, cart, and common are enforced.
- The seven customer events are mapped to persisted source-of-truth events.
- Transactional and marketing messages are distinct.
- Marketing consent and opt-outs are enforced before dispatch.
- Celery tasks run asynchronously and only after the relevant transaction commits.
- Duplicate processing is controlled to the extent supported by the selected delivery interfaces.
- Failures are bounded, observable, and isolated from business transactions.
- Minimal delivery history is available without storing sensitive payloads.
- Staff alerts are restricted to configured recipients.
- Disabled or unconfigured channels fail safely.
- No real messages are sent during automated tests.
- Provider credentials and message templates are configured through approved mechanisms.
- Production delivery has been verified using approved test recipients.
- Required account-security delivery workflows have a defined and tested channel.
- Applicable consent, privacy, and channel-specific compliance requirements have been reviewed.

## 21. Non-goals for launch

Unless separately approved, do not implement:

- A full campaign-management platform.
- Marketing automation journeys or customer segmentation.
- A notification analytics dashboard.
- A complex template-management UI.
- Delivery guarantees beyond the capabilities of the selected broker and provider.
- Automatic SMS fallback to another channel without a defined policy.
- Automatic marketing consent based on order creation.
- Automatic payment expiry or refund workflows.
- Order cancellation or fulfillment logic inside notifications.
- Delivery tracking for home delivery, since Leeza Cakes is takeaway/pickup only.

---

**Final architectural rule:** `notifications` delivers messages about authoritative business events. `accounts`, `orders`, and `payments` remain responsible for deciding whether those events are valid. WhatsApp, SMS, email, and Celery are delivery infrastructure, not sources of business truth.