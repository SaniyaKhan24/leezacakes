# Accounts App — Architecture and Structure

**Project:** Leeza Cakes  
**Django application:** `apps.accounts`  
**Document type:** Architecture specification  
**Status:** Architecture defined; implementation pending  
**Audience:** AI coding agents, backend developers, reviewers, and maintainers

---

## 1. Purpose and Scope

The `accounts` application is responsible for customer identity, authentication, account lifecycle, personal profile information, and customer-owned saved addresses.

It is the single source of truth for user identity throughout the Leeza Cakes platform.

The application must provide a secure, maintainable foundation that supports the current e-commerce requirements and future capabilities without coupling identity logic to individual business applications.

### Responsibilities

The accounts application owns:

- Customer registration.
- User model and identity fields.
- Login and logout.
- Authentication token lifecycle.
- Email verification.
- Password changes and password recovery.
- Customer profile management.
- Saved customer addresses.
- Account activation and deactivation.
- Account deletion or anonymization workflows, subject to legal and operational requirements.
- Authentication-related permissions and policies.
- Account-related notifications through the notification application.
- Authentication audit events and security-sensitive account activity.

### Explicitly outside its scope

The accounts application must not own:

- Product or category management — `apps.catalog`.
- Shopping cart state — `apps.cart`.
- Cake customization and customization options — `apps.customization`.
- Order creation, order status, and order history — `apps.orders`.
- Payment processing, payment status, and refunds — `apps.payments`.
- Global product search — `apps.search`.
- General-purpose notification delivery infrastructure — `apps.notifications`.
- Shared API infrastructure and generic utilities — `apps.common`.

The accounts application may integrate with these applications through well-defined interfaces, but it must not duplicate their data or business logic.

---

## 2. Architectural Principles

The implementation must follow these principles.

1. **Single identity source:** Every application references the same Django user model.
2. **Security by default:** Authentication, authorization, validation, and ownership checks are mandatory.
3. **Separation of concerns:** HTTP handling, serialization, business rules, database queries, and external integrations remain separate.
4. **Explicit ownership:** Customers may access only their own private account data and saved addresses.
5. **Minimal personal data:** Collect only information required for a documented business purpose.
6. **No trust in client-supplied identity:** The server determines the authenticated user from validated credentials.
7. **Transactional integrity:** Multi-step database operations use transactions where partial completion would cause inconsistent state.
8. **No hidden side effects:** Email delivery and other external operations must not silently become part of unrelated database operations.
9. **Testability:** Business logic must be testable without sending real emails or calling external services.
10. **API stability:** Changes to account endpoints must be deliberate, documented, and tested.
11. **Auditable security events:** Sensitive actions must be observable without logging passwords, tokens, or unnecessary personal information.
12. **No premature abstraction:** Introduce interfaces and shared utilities when there is a concrete need; avoid unnecessary layers and empty modules.

---

## 3. Recommended Directory Structure

Implement the following structure under `backend/apps/accounts/`.

```text
accounts/
├── __init__.py
├── apps.py
├── models.py
├── managers.py
├── admin.py
├── permissions.py
├── serializers.py
├── filters.py
├── pagination.py
├── urls.py
├── views.py
├── selectors.py
├── services.py
├── constants.py
├── exceptions.py
├── validators.py
├── signals.py
├── tasks.py
├── throttles.py
├── authentication.py
├── tokens.py
├── migrations/
│   └── __init__.py
└── tests/
    ├── __init__.py
    ├── factories.py
    ├── test_models.py
    ├── test_managers.py
    ├── test_serializers.py
    ├── test_permissions.py
    ├── test_services.py
    ├── test_selectors.py
    ├── test_authentication.py
    ├── test_registration.py
    ├── test_login.py
    ├── test_verification.py
    ├── test_password_reset.py
    ├── test_profile.py
    ├── test_addresses.py
    └── test_api.py
```

Create a module only when it has an actual implementation purpose. If a component does not need custom behavior, use the appropriate Django or DRF functionality rather than adding an empty abstraction.

### Module responsibilities

| Module | Responsibility |
|---|---|
| `apps.py` | Django application configuration |
| `models.py` | User, customer profile if needed, saved address, verification records |
| `managers.py` | User creation and superuser creation |
| `admin.py` | Secure Django admin configuration |
| `serializers.py` | Request validation and response serialization |
| `views.py` | API request handling and HTTP responses |
| `urls.py` | Accounts endpoint routing |
| `services.py` | Registration, verification, password and account lifecycle operations |
| `selectors.py` | Read-only database queries |
| `permissions.py` | Account-level access and ownership policies |
| `authentication.py` | Custom authentication integration only if required |
| `tokens.py` | Token policy and lifecycle integration if required |
| `validators.py` | Reusable account-specific validation |
| `constants.py` | Stable account-related constants |
| `exceptions.py` | Account domain exceptions and mappings |
| `signals.py` | Minimal Django signal integration, if genuinely required |
| `tasks.py` | Asynchronous account operations, if a task queue is configured |
| `throttles.py` | Endpoint-specific throttling policies |
| `filters.py` | Administrative or authorized account-query filtering if needed |
| `pagination.py` | Pagination for authorized account listings if needed |
| `tests/` | Isolated tests for each architectural responsibility |

The accounts app must not become a generic dumping ground for functionality belonging to other applications.

---

## 4. User Identity and Database Design

### 4.1 Custom user model

**Decision required before the first database migration:** determine whether a custom user model is needed.

For Leeza Cakes, the recommended design is a custom email-based user model extending Django's `AbstractUser`, with username authentication removed and a normalized, unique email address used for login.

The implementation should use:

- `apps.accounts.models.User`
- `apps.accounts.managers.UserManager`
- `AUTH_USER_MODEL = "accounts.User"`

This decision must be implemented before the first migration that creates the authentication tables. If initial migrations have already been applied in any environment, inspect the database and migration history before changing the user model.

Do not create a second user model alongside Django's built-in user model.

### 4.2 User model fields

The recommended user model contains:

| Field | Purpose |
|---|---|
| `id` | Primary key, preferably UUID if consistent with the overall project design |
| `email` | Required, unique login identifier |
| `first_name` | Customer's first name |
| `last_name` | Customer's last name |
| `phone_number` | Optional phone number if required for customer communication |
| `is_active` | Controls whether the account can authenticate |
| `is_staff` | Controls Django admin access |
| `is_superuser` | Django administrative permission flag |
| `is_email_verified` | Records successful email verification |
| `date_joined` | Account creation timestamp |
| `last_login` | Last successful login timestamp, managed appropriately by Django |

Use Django's standard permission and group system. Do not introduce an arbitrary `role` field unless there is a documented requirement for application-level roles.

Do not store passwords manually. Use Django's password hashing and authentication mechanisms.

If UUID primary keys are adopted, ensure all related models, serializers, URLs, tests, and migrations use them consistently.

### 4.3 Email normalization

Email addresses must be validated and normalized consistently.

- Trim surrounding whitespace.
- Apply the chosen normalization policy in one place.
- Use a database uniqueness constraint.
- Prevent duplicate accounts caused by inconsistent normalization.
- Do not rely on a serializer-only uniqueness check; concurrent requests must still be protected by the database constraint.
- Handle uniqueness violations safely without exposing internal database errors.

Do not make provider-specific assumptions about email address equivalence beyond the documented normalization policy.

### 4.4 User manager

The custom manager must correctly implement:

- `create_user()`
- `create_superuser()`

It must normalize email addresses, hash passwords, validate required fields, and enforce Django's expected superuser flags.

Superusers must never be created through public registration endpoints.

### 4.5 Profile model

Avoid creating a separate `CustomerProfile` model merely to duplicate fields already stored on the user.

Introduce a one-to-one profile model only when additional profile information has a distinct lifecycle or clear business purpose. If used, the relationship must reference `settings.AUTH_USER_MODEL`, not a hard-coded user model.

Do not collect unnecessary demographic or sensitive personal information.

---

## 5. Saved Customer Addresses

The accounts application may own saved customer addresses because these are part of the customer's personal account.

Recommended model: `Address`.

Suggested fields:

- `id`
- `user`
- `label`, such as Home or Work
- `recipient_name`
- `phone_number`
- `address_line_1`
- `address_line_2`, optional
- `locality`
- `city`
- `state`
- `postal_code`
- `country_code`
- `is_default`
- `created_at`
- `updated_at`

Use a foreign key to `settings.AUTH_USER_MODEL` with a deliberate deletion policy.

### Address invariants

- Every saved address belongs to exactly one user.
- Customers cannot read, edit, delete, or set as default another customer's address.
- A customer may have at most one default saved address, enforced transactionally and, where supported by the selected database, with an appropriate database constraint.
- Address validation must be centralized.
- Country and postal-code validation should not assume that every customer is located in India.
- Do not expose internal database identifiers or other customers' addresses through public account endpoints.

### Relationship with orders

An order must retain the shipping and billing details that applied when the order was placed.

The orders application must store an appropriate address snapshot on the order or its associated address records. It must not depend on a customer's saved address remaining unchanged.

Editing or deleting a saved address must not silently rewrite historical order details.

The accounts application owns saved addresses. The orders application owns order-address snapshots.

---

## 6. Authentication Architecture

The accounts application must support a defined authentication lifecycle.

### 6.1 Registration

Expected flow:

1. Receive registration details.
2. Validate the request.
3. Normalize the email address.
4. Validate the password using Django's configured password validators.
5. Create the account with a securely hashed password.
6. Establish the initial account status according to the chosen verification policy.
7. Generate a verification challenge when required.
8. Schedule the verification notification through the notification layer.
9. Return a safe response that does not reveal passwords, tokens, or internal model details.

Registration must be transactional where necessary.

Email verification and account activation are separate concepts. A verified email address does not automatically grant staff privileges.

The project must choose whether unverified users can authenticate and, if permitted, which operations remain unavailable until verification.

### 6.2 Login

The login flow must:

1. Validate the supplied credentials.
2. Authenticate using Django's supported authentication mechanisms.
3. Enforce account-active and applicable verification policies.
4. Apply rate limiting.
5. Return the configured authentication response.
6. Record safe security metadata when appropriate.

Invalid credentials should produce a generic response. Do not reveal whether an email address is registered or whether a particular account is inactive.

### 6.3 Authentication mechanism

The Next.js frontend and Django backend must use one deliberately selected authentication strategy.

Recommended option for a separate frontend: a maintained JWT integration such as `djangorestframework-simplejwt`, with short-lived access tokens, refresh-token rotation, and refresh-token revocation/blacklisting where appropriate.

If refresh tokens are stored in cookies, configure `HttpOnly`, `Secure`, an appropriate `SameSite` policy, CSRF protection for cookie-authenticated state-changing requests, and correct CORS settings.

Do not store long-lived refresh tokens in browser local storage.

Before implementation, verify that the authentication dependencies are present and compatible. Do not assume that the existing requirements already include Simple JWT.

An alternative cookie-based session architecture is acceptable if selected deliberately and documented. Do not implement JWT and session authentication as competing systems without a clear use case.

### 6.4 Logout and revocation

Logout must follow the selected authentication architecture.

For a token-based design:

- Revoke or blacklist refresh tokens where supported.
- Clear authentication cookies when cookies are used.
- Define how access tokens remain valid until expiry or how they can be revoked if immediate revocation is required.
- Ensure repeated logout requests are handled predictably.

For session authentication, invalidate the active session and clear session cookies as appropriate.

### 6.5 Password change

Authenticated customers may change their password by supplying the current password and a valid new password.

The operation must:

- Verify the current password.
- Validate the new password using Django's configured validators.
- Store the password through Django's password-setting API.
- Apply the chosen session or token invalidation policy.
- Avoid returning sensitive password information.

### 6.6 Password recovery

Password recovery must not disclose whether an account exists.

Expected flow:

1. Accept an email address.
2. Return a generic success response.
3. Generate a secure, time-limited reset challenge for eligible accounts.
4. Deliver the reset link through the notification layer.
5. Validate the challenge and expiry.
6. Update the password securely.
7. Invalidate the reset challenge and revoke applicable authentication sessions or tokens.
8. Record a safe audit event.

Use Django's established password-reset mechanisms where appropriate instead of inventing an insecure token protocol.

### 6.7 Email verification

Verification challenges must be:

- Unpredictable and cryptographically secure.
- Time-limited.
- Single-use.
- Bound to the intended account and purpose.
- Stored securely; store a digest rather than a reusable raw secret where appropriate.
- Rate-limited.
- Invalidated after successful verification.
- Invalidated or superseded when a replacement challenge is issued.

Do not place passwords, access tokens, or other long-lived credentials in verification URLs.

### 6.8 Social authentication

Do not add Google, Apple, or other social login integrations until the project explicitly requires them. They introduce additional dependencies, OAuth configuration, callback security requirements, and account-linking decisions.

---

## 7. Token and Verification Data

If persistent verification records are needed, use a dedicated model such as `AccountVerificationToken` or a similarly named model with a clearly defined purpose.

Potential fields:

- `id`
- `user`
- `purpose`
- `token_digest`
- `expires_at`
- `used_at`
- `created_at`

The exact design should reuse Django's established mechanisms where possible.

Requirements:

- Enforce expiry and single-use behavior.
- Avoid storing reusable raw tokens.
- Prevent tokens from being used for the wrong purpose.
- Invalidate prior challenges according to the documented replacement policy.
- Ensure concurrent requests cannot successfully consume the same challenge twice.
- Never log raw token values.
- Avoid storing sensitive information that can be derived from the related user.

Do not create a separate token model if the selected framework already provides a suitable, secure implementation and a custom model offers no meaningful benefit.

---

## 8. Layered Application Architecture

The request path should follow this structure:

```text
HTTP Request
    |
    v
config.urls
    |
    v
apps.accounts.urls
    |
    v
Authentication and Throttling
    |
    v
Permission Checks
    |
    v
View / API Endpoint
    |
    v
Serializer Validation
    |
    v
Account Service
    |
    +-------> Selectors / ORM Queries
    |
    +-------> Account Models
    |
    +-------> Notification Interface
    |
    +-------> Security Audit Events
    |
    v
Serializer / Response
    |
    v
HTTP Response
```

Not every endpoint requires a service, selector, and separate permission class. Use the layers when they improve clarity, reuse, security, or testability.

### Views

Views are responsible for:

- Parsing requests.
- Applying authentication and permissions.
- Invoking validation and business operations.
- Translating outcomes into HTTP responses.
- Selecting appropriate status codes.

Views must not contain large business workflows or duplicate account rules.

### Serializers

Serializers are responsible for:

- Input validation.
- Output representation.
- Preventing unauthorized field updates.
- Enforcing field-level restrictions.
- Returning explicit, safe response data.

Registration serializers must never return password fields. Profile update serializers must not allow customers to modify `is_staff`, `is_superuser`, `is_active`, verification flags, or other administrative state.

### Services

Services own multi-step business operations, such as:

- Account registration.
- Email verification.
- Password reset completion.
- Password change.
- Address creation and default-address changes.
- Account deactivation or deletion workflows.

Services must enforce business invariants even when called from outside an HTTP view.

Use `transaction.atomic()` for operations requiring atomic database changes. Do not assume a database transaction can roll back an already-sent email or other external side effect.

### Selectors

Selectors contain reusable read-only queries, such as:

- Retrieving the current customer's profile.
- Listing a customer's saved addresses.
- Retrieving an address with ownership restrictions.
- Fetching authorized account information for internal workflows.

Selectors must not bypass authorization requirements or expose another customer's private records.

### Permissions

Permissions determine whether an authenticated principal may perform an action.

Use DRF's authentication and permission framework. Prefer explicit, testable permission rules over scattered checks.

Object ownership must be checked for every private resource. Returning a 404 instead of a 403 may be appropriate when concealing another customer's resource existence, but the behavior must be consistent and documented.

### Exceptions

Define a small set of account-domain exceptions only where they improve consistency. Map expected failures to safe API responses without exposing stack traces, database errors, or internal implementation details.

### Signals

Signals must not become the main business workflow mechanism.

Use explicit service calls for required operations. Signals may be used for limited integration purposes when their execution order and failure behavior are understood and tested.

### Background tasks

Use `tasks.py` only when a task queue is configured and a real asynchronous task is needed. Email sending may be delegated through the notifications application or a task queue.

Do not add Celery or another broker merely to populate a folder.

---

## 9. Integration With Other Applications

| Application | Relationship with accounts |
|---|---|
| `apps.common` | Shared infrastructure, common exceptions, health checks, and genuinely reusable utilities |
| `apps.catalog` | Catalogue data remains independent of account identity; administrative operations use Django permissions |
| `apps.customization` | Customer identity may be associated with saved or submitted customizations when required |
| `apps.cart` | Cart ownership references the configured user model or a deliberately designed guest-cart identity |
| `apps.orders` | Orders reference the customer and preserve order-specific customer/address snapshots |
| `apps.payments` | Payment ownership is derived from the associated order; identity alone never proves payment |
| `apps.notifications` | Delivers account verification, password reset, and other account notifications |
| `apps.search` | Search queries catalogue data and does not own user identity |
| Django admin | Uses the configured user model and Django's staff, group, and permission mechanisms |

### Integration rules

- Other applications must reference `settings.AUTH_USER_MODEL` in model definitions.
- Avoid circular imports between application models.
- Use lazy model references where appropriate.
- Do not import account models into every module unnecessarily.
- Notifications must receive only the data required to deliver the message.
- The payments application must never trust client-supplied user identity or payment status.
- Cart and order services must derive customer identity from a trusted authenticated context.
- Avoid cross-app database updates hidden inside signals.

---

## 10. API and Versioning Boundaries

The accounts API must be mounted beneath the project's versioned API prefix.

Recommended prefix:

`/api/v1/accounts/`

Exact endpoint paths, request schemas, response schemas, and HTTP status codes belong in `accounts_api.md`.

The structure document defines responsibilities and invariants; it does not replace the detailed API specification.

Every endpoint must document:

- Authentication requirements.
- Authorization requirements.
- Input validation.
- Expected successful behavior.
- Error behavior.
- Rate limiting.
- Whether the endpoint changes persistent state.
- Relevant tests.

All endpoints must use DRF's standard request/response handling and contribute to the generated OpenAPI schema.

---

## 11. Security Requirements

### Authentication and authorization

- Deny access by default for private account resources.
- Never trust a user ID supplied by the client to determine the current user.
- Derive the authenticated identity from validated credentials.
- Enforce ownership checks for every private account object.
- Keep administrative privileges separate from customer privileges.
- Never permit public registration to create staff or superuser accounts.

### Password security

- Use Django's password hashers.
- Apply appropriate password validators.
- Never store plaintext passwords.
- Never log passwords.
- Do not implement custom password hashing.
- Rate-limit login and password recovery endpoints.

### Token security

- Use cryptographically secure token generation.
- Enforce expiry and purpose restrictions.
- Avoid logging token values.
- Apply appropriate revocation and rotation policies.
- Protect cookie-based authentication against CSRF where applicable.

### API security

- Validate all user input.
- Use explicit serializer fields.
- Protect against mass assignment.
- Restrict CORS to approved frontend origins.
- Configure throttling for sensitive operations.
- Use generic authentication and password-reset errors.
- Never expose internal exception details in production.

### Personal data

- Return only necessary fields.
- Do not expose password hashes, internal security flags, verification secrets, or administrative metadata.
- Restrict account listings to authorized administrative operations.
- Avoid logging full addresses, phone numbers, or email contents unnecessarily.
- Define retention and deletion behavior for personal data.
- Preserve legally or operationally required order records when accounts are deactivated or deleted.

### Auditability

Record meaningful security events such as:

- Successful and failed authentication attempts, subject to privacy-conscious logging.
- Password changes and resets.
- Email verification.
- Account deactivation.
- Administrative changes to account privileges.

Audit records must not contain passwords, raw tokens, or unnecessary sensitive data.

---

## 12. Transaction and Concurrency Rules

Operations that modify related state must handle concurrency correctly.

Examples:

- Registration must handle duplicate-email races through database constraints.
- Email verification must not allow the same challenge to be consumed twice.
- Default-address changes must not leave multiple default addresses for the same customer.
- Password-reset completion must invalidate the challenge safely.
- Account deactivation must apply the defined session or token policy.
- Deletion workflows must respect order and payment retention requirements.

Use database constraints as the final enforcement layer for data invariants where possible.

Do not rely exclusively on application-level validation for uniqueness or other concurrent operations.

External actions such as email delivery must have a clear failure policy. Use `transaction.on_commit()` where appropriate, and use a durable task or outbox mechanism if reliable delivery is a business requirement.

---

## 13. Django Admin

Configure the custom user model correctly in `admin.py`.

Requirements:

- Provide appropriate list displays, search, and filters.
- Never display password hashes unnecessarily.
- Restrict sensitive user fields to authorized staff.
- Prevent ordinary staff users from granting themselves elevated privileges.
- Protect verification and token records from inappropriate access.
- Ensure staff permissions follow Django's authorization system.
- Avoid registering duplicate or incompatible user models.

Admin functionality must be tested separately from public account endpoints.

---

## 14. Testing Strategy

The accounts application must have tests at the model, service, permission, and API levels.

### Model tests

Verify:

- User creation.
- Password hashing.
- Email normalization.
- Email uniqueness.
- User manager behavior.
- Superuser invariants.
- Address ownership relationships.
- Relevant database constraints.

### Authentication tests

Verify:

- Valid login.
- Invalid credentials.
- Inactive-account behavior.
- Email-verification policy.
- Logout and revocation behavior.
- Token expiry and rotation where applicable.
- Authentication throttling.

### Registration and verification tests

Verify:

- Valid registration.
- Invalid input.
- Duplicate-email races where practical.
- Safe verification delivery.
- Expired verification challenges.
- Reuse of consumed challenges.
- Correct activation and verification policy.

### Password tests

Verify:

- Current-password validation.
- Password policy enforcement.
- Valid password-reset flow.
- Expired and invalid reset challenges.
- Single-use reset behavior.
- Relevant session or token invalidation.

### Authorization tests

Verify:

- Anonymous access is rejected where required.
- A customer can access their own resources.
- A customer cannot access another customer's resources.
- A customer cannot modify administrative fields.
- Staff permissions behave as intended.
- Address ownership is enforced for read, update, delete, and default selection.

### API tests

Verify:

- Correct status codes.
- Correct response shapes.
- Input validation.
- Error response consistency.
- Throttling.
- OpenAPI schema inclusion.
- No sensitive fields in serialized responses.

Tests must use isolated test data and must never depend on or mutate production Supabase data.

External email delivery must be mocked or replaced with a test backend during tests.

---

## 15. Observability and Operational Behavior

The accounts application must integrate with the project's logging and monitoring conventions.

- Use structured, actionable logs.
- Avoid logging credentials or raw tokens.
- Report expected validation failures without unnecessary error-level noise.
- Capture unexpected failures with enough context for debugging, excluding sensitive data.
- Ensure security events can be distinguished from ordinary application logs.
- Keep health checks free of private account data.
- Do not create a public endpoint that enumerates accounts or exposes authentication status.

If a security audit log model is introduced, define its access controls, retention, and data-minimization policy explicitly.

---

## 16. Environment Configuration

Read configuration from environment variables through the project's established settings infrastructure.

Potential settings include:

- Authentication token lifetimes.
- Verification token lifetime.
- Password-reset lifetime.
- Account verification policy.
- Allowed frontend origins.
- Email provider configuration.
- Throttling rates.
- Optional task-queue configuration.

Do not hard-code secrets, provider credentials, or production URLs.

Do not add a large number of environment variables unless the application actually uses them. Each variable must be documented in `.env.example` with a safe placeholder and a clear description.

---

## 17. Implementation Order

Implement the accounts application in this order:

1. Inspect the existing project, Django version, installed dependencies, settings, app configuration, and migration history.
2. Decide and document the custom user model before the first migration.
3. Implement the user model, manager, admin integration, and model tests.
4. Configure authentication and the chosen token or session policy.
5. Implement registration and login services and endpoints.
6. Implement email verification and notification integration.
7. Implement password change and password recovery.
8. Implement customer profile retrieval and updates.
9. Implement saved addresses and ownership protections.
10. Implement account deactivation and any approved deletion workflow.
11. Add throttling, audit events, and security tests.
12. Document every endpoint in `accounts_api.md`.
13. Validate the OpenAPI schema.
14. Run Ruff, Django checks, migration consistency checks, and tests.
15. Review the final diff for accidental secrets, unapproved migrations, and unrelated changes.

Do not run database migrations against Supabase without explicit approval.

---

## 18. Definition of Done

The accounts application is considered implemented only when:

- [ ] The user-model decision is documented and correctly configured.
- [ ] The user manager and admin integration work.
- [ ] Authentication follows one documented strategy.
- [ ] Registration, verification, and password recovery are implemented if required by the agreed product scope.
- [ ] Profile and address ownership rules are enforced.
- [ ] Other applications reference the configured user model correctly.
- [ ] Input serializers reject unauthorized fields.
- [ ] Authentication and authorization tests pass.
- [ ] Password and verification flows are tested.
- [ ] API endpoints appear in the OpenAPI schema.
- [ ] Ruff linting and formatting checks pass.
- [ ] Django development checks pass.
- [ ] Production configuration checks pass with valid synthetic configuration.
- [ ] Migration consistency checks pass.
- [ ] The full test suite passes.
- [ ] No secrets or personal data are exposed through logs or API responses.
- [ ] The implementation and endpoints are documented.
- [ ] No database migrations or production changes have been executed without approval.

A passing test suite establishes evidence for the tested behavior; it does not, by itself, prove that the application is secure or production-ready.

---

## 19. Instructions for AI Coding Agents

When implementing this specification:

1. Inspect the repository before editing.
2. Follow the existing project conventions where they do not conflict with this architecture.
3. Do not invent requirements or unnecessary features.
4. Do not silently change authentication strategy or user-model decisions.
5. Do not duplicate business logic across applications.
6. Do not trust client-provided identity, ownership, verification status, or administrative flags.
7. Do not run migrations, reset databases, push commits, or deploy without explicit approval.
8. Implement actual behavior and tests instead of creating empty placeholder files.
9. Update `accounts_api.md` whenever endpoint behavior changes.
10. Report implemented functionality, test results, limitations, and outstanding decisions honestly.

**This document defines the architectural contract for `apps.accounts`.** Detailed endpoint definitions belong in `accounts_api.md`; application-wide security settings and cross-application conventions belong in the relevant backend architecture documentation.