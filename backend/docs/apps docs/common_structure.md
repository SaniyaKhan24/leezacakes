# Common App — Architecture and Structure

**Project:** Leeza Cakes  
**Django application:** `apps.common`  
**Document type:** Architecture specification  
**Status:** Architecture defined; implementation pending  
**Audience:** AI coding agents, backend developers, reviewers, and maintainers

---

## 1. Purpose

The `common` application provides reusable, application-wide infrastructure for the Leeza Cakes backend.

Its purpose is to standardize genuinely shared concerns so individual applications do not independently implement the same API conventions, exceptions, validators, pagination behavior, or operational endpoints.

The common app must remain small, stable, and independent of application-specific business rules.

### Responsibilities

The common app may own:

- Shared API response conventions, if the project adopts a response envelope.
- Common exception classes and exception-response formatting.
- Reusable pagination classes.
- Reusable validators that have no specific business-domain ownership.
- Health and readiness endpoints.
- Shared constants that genuinely apply across applications.
- Common API metadata and utility functions.
- Safe request-correlation identifiers and related middleware, if needed.
- Small, framework-independent helpers used by multiple applications.

### Responsibilities it must not own

The common app must not own:

- User registration, authentication, or profiles — `apps.accounts`.
- Products, categories, catalogue pricing, or inventory — `apps.catalog`.
- Cake personalization rules — `apps.customization`.
- Cart calculations — `apps.cart`.
- Order lifecycle or checkout logic — `apps.orders`.
- Payment processing or refunds — `apps.payments`.
- Email delivery or notification templates — `apps.notifications`.
- Product search — `apps.search`.
- Application-wide settings that belong in `config/settings/`.
- Generic wrappers around every Django or DRF feature.
- Business logic merely because multiple apps might eventually use it.

Do not turn `common` into a miscellaneous collection of unrelated utilities.

---

## 2. Architectural Principles

1. **Minimal shared surface:** Add functionality only when it is genuinely shared or belongs to operational infrastructure.
2. **Low coupling:** Common modules must not import business models from accounts, catalogue, orders, payments, or other domain apps.
3. **Stable contracts:** Shared exceptions, pagination behavior, and response formats must not change casually.
4. **Explicit behavior:** Avoid hidden response transformations, implicit database access, or unexpected side effects.
5. **Security by default:** Shared utilities must not bypass authentication, permissions, validation, or safe error handling.
6. **Framework compatibility:** Use Django and DRF capabilities directly when they already solve the problem well.
7. **Testability:** Each shared component must have focused unit or integration tests.
8. **No premature abstraction:** Do not create generic base classes, factories, mixins, or utility layers without a concrete need.
9. **Operational separation:** Health checks must distinguish process availability from dependency readiness where necessary.
10. **Observable failures:** Unexpected failures must be diagnosable through server-side logs without leaking internal details to clients.

---

## 3. Recommended Directory Structure

Use this structure under `backend/apps/common/` as needed.

```text
common/
├── __init__.py
├── apps.py
├── admin.py
├── models.py
├── constants.py
├── exceptions.py
├── pagination.py
├── validators.py
├── responses.py
├── middleware.py
├── urls.py
├── views.py
├── health.py
├── utils.py
├── migrations/
│   └── __init__.py
└── tests/
    ├── __init__.py
    ├── test_exceptions.py
    ├── test_pagination.py
    ├── test_validators.py
    ├── test_responses.py
    ├── test_middleware.py
    ├── test_health.py
    └── test_api.py
```

This is a set of optional modules, not a requirement to create empty files.

Keep the following rules:

- `models.py` should remain empty of domain data unless common infrastructure genuinely requires persistence.
- `admin.py` should contain no registrations unless the app owns an administrative model.
- `middleware.py` should be used only for cross-cutting request processing that cannot be handled more simply elsewhere.
- `utils.py` must not become a catch-all. Prefer named modules with specific responsibilities.
- Keep health-check logic in `health.py` and HTTP view wiring in `views.py`.
- Add tests only for implemented components.

---

## 4. Module Responsibilities

| Module | Responsibility |
|---|---|
| `apps.py` | Django application configuration |
| `constants.py` | Small set of stable, genuinely shared constants |
| `exceptions.py` | Shared exception classes and exception normalization |
| `pagination.py` | Reusable DRF pagination classes |
| `validators.py` | Domain-independent validation helpers |
| `responses.py` | Shared response helpers only if a common response convention is adopted |
| `middleware.py` | Optional request-correlation or other justified cross-cutting middleware |
| `urls.py` | Routes owned by the common app |
| `views.py` | Shared operational HTTP views, including health endpoints |
| `health.py` | Health and readiness evaluation |
| `utils.py` | Small pure utilities with a clearly defined purpose |
| `models.py` | Shared persistence only if a real requirement emerges |
| `admin.py` | Admin integration for models owned by this app |
| `tests/` | Tests for each implemented shared component |

Do not implement custom behavior when Django or DRF already provides an appropriate standard mechanism.

---

## 5. Shared API Response Convention

### 5.1 Decision

Before implementing a global response wrapper, inspect the existing API architecture.

DRF already supports normal JSON responses and validation-error formats. A custom response envelope is optional, not mandatory.

If the project adopts a shared success envelope, document it and apply it consistently across endpoints. For example:

```json
{
  "data": {
    "id": "example-id"
  }
}
```

If the project does not adopt an envelope, retain conventional DRF responses instead.

Do not wrap some endpoints in `data` while leaving others inconsistent without a documented reason.

### 5.2 Requirements

If `responses.py` is implemented, it may provide small helpers for common response shapes.

It must not:

- Hide HTTP status codes.
- Swallow exceptions.
- Return HTTP `200` for failed operations.
- Expose database exceptions.
- Automatically serialize arbitrary Django models.
- Duplicate serializers.
- Force success envelopes onto streaming, file, schema, or other specialized responses.

The response policy must be established before implementing many application endpoints.

---

## 6. Shared Exception Handling

### 6.1 Purpose

`exceptions.py` should define only exceptions that genuinely cross application boundaries or shared response-formatting behavior.

Django and DRF already define many appropriate exception classes. Reuse them rather than building a competing hierarchy.

### 6.2 Responsibilities

The shared exception strategy should:

- Normalize expected API errors.
- Preserve correct HTTP status codes.
- Return consistent validation errors.
- Avoid exposing stack traces or internal exception details.
- Allow unexpected exceptions to be logged and reported as generic server errors.
- Preserve safe field-level validation messages.

### 6.3 Business exceptions

Domain-specific exceptions should normally live in the owning application.

Examples:

- Invalid account verification belongs to `apps.accounts`.
- Unavailable products belong to `apps.catalog`.
- Invalid customization belongs to `apps.customization`.
- Invalid cart operations belong to `apps.cart`.
- Invalid order transitions belong to `apps.orders`.
- Payment-provider failures belong to `apps.payments`.

The common app may provide a small shared base exception only if there is a concrete need.

Never convert every exception into a generic successful response or hide failures from monitoring.

---

## 7. Pagination

### 7.1 Purpose

`pagination.py` may define a reusable pagination policy for list endpoints.

Use DRF's built-in pagination classes where they meet the requirements.

### 7.2 Requirements

- Set pagination behavior centrally where appropriate.
- Validate page sizes and page parameters.
- Enforce a maximum page size.
- Avoid unbounded queries for large datasets.
- Ensure ordering is deterministic.
- Preserve authorization and filtering applied by the underlying queryset.
- Document the response structure.
- Avoid pagination for endpoints where it is not meaningful.

Catalogue, order, and address endpoints must apply their own access restrictions before returning paginated data.

Do not introduce custom cursor pagination unless there is a concrete performance or consistency requirement.

---

## 8. Shared Validators

The common app may contain validators that are independent of any business domain.

Potential examples include:

- Generic non-empty input validation.
- Reusable file-size checks when the rule is genuinely global.
- Shared primitive format validation.
- Common identifier validation where a single policy is used across applications.

The following should remain in their domain applications:

- Email identity and account-specific verification rules — `apps.accounts`.
- Product price and stock rules — `apps.catalog`.
- Cake customization rules — `apps.customization`.
- Cart quantity and pricing rules — `apps.cart`.
- Order transition rules — `apps.orders`.
- Payment amount, signature, and provider-specific validation — `apps.payments`.

Use Django and DRF validators when they are sufficient. Do not duplicate built-in validators under new names.

Validators must be deterministic, side-effect-free, and straightforward to test wherever practical.

---

## 9. Health and Readiness Endpoints

The common app owns lightweight operational health endpoints.

Recommended routes:

- `GET /health/live/`
- `GET /health/ready/`

These routes are mounted through the project's root URL configuration. Their exact paths must not conflict with other routes.

### 9.1 Liveness

The liveness endpoint answers:

**Is the application process running and able to serve requests?**

It should perform minimal work and should not depend on the database, email provider, payment provider, or other external services.

Example:

```json
{
  "status": "ok"
}
```

Return HTTP `200` when the application is alive.

### 9.2 Readiness

The readiness endpoint answers:

**Is the application ready to handle the operations that require its configured dependencies?**

The implementation may verify essential dependencies, such as database connectivity, using short, bounded checks.

Requirements:

- Do not run expensive queries.
- Do not expose database hostnames, usernames, credentials, stack traces, or connection details.
- Use bounded timeouts.
- Return an appropriate non-success status if an essential dependency is unavailable.
- Keep optional providers from making the whole application unavailable unless the business policy requires them.
- Avoid retry storms caused by aggressive health-check frequency.

Do not require email or payment-provider availability for liveness.

Whether database connectivity is part of readiness must be documented for the actual deployment platform.

### 9.3 Access control

Health endpoints may be public if the deployment requires them, but their responses must reveal minimal information.

Do not expose detailed dependency diagnostics through an unauthenticated public endpoint.

---

## 10. Request-Correlation Middleware

### 10.1 When to implement

Implement custom middleware only if the project requires a request-correlation identifier and the logging platform does not already provide an equivalent mechanism.

Do not add middleware merely because the file exists in the proposed structure.

### 10.2 Responsibilities

If implemented, middleware should:

- Accept a valid correlation identifier according to a documented policy or generate one.
- Validate length and permitted characters.
- Attach the identifier to request context.
- Include the identifier in appropriate response headers.
- Make the identifier available to structured logging.
- Avoid storing request bodies or sensitive headers in logs.

Never trust arbitrary request headers as authentication evidence or authorization input.

Do not log passwords, authorization headers, cookies, access tokens, refresh tokens, verification tokens, or reset tokens.

Middleware must not unexpectedly alter business responses or swallow exceptions.

---

## 11. Shared Constants and Utilities

### Constants

`constants.py` may contain stable values shared across multiple apps.

Do not store all project settings here. Environment-specific values belong in `config/settings/`.

Avoid duplicating the same constant across apps when it represents a single, stable shared policy.

### Utilities

`utils.py` should contain small, pure helpers only when a clearly named module is not more appropriate.

A helper belongs in common only when it is independent of business-domain behavior and has multiple legitimate consumers or a clear infrastructure purpose.

Avoid:

- Generic service base classes.
- Arbitrary model mixins.
- Global mutable state.
- Hidden database queries.
- Importing all application models into common.
- Functions that bypass permission checks.
- A utility module containing unrelated business workflows.

---

## 12. Database and Models

The common app should not own business data.

Keep `models.py` free of unnecessary models.

A shared persistent model should be introduced only when it represents a real cross-application concept with a clear owner and lifecycle.

If a database model is added:

- Define explicit fields and constraints.
- Document ownership and retention.
- Add migrations deliberately.
- Add tests for model behavior.
- Avoid references to specific business models unless required by a documented design.
- Do not create a generic table for arbitrary JSON records as a substitute for proper domain modeling.

Health checks, response helpers, pagination, and validators do not require database models.

---

## 13. Application Dependencies and Import Boundaries

The common app is a low-level dependency.

Preferred dependency direction:

```text
config
  |
  v
apps.common
  |
  v
domain applications
  |
  +--> accounts
  +--> catalog
  +--> customization
  +--> cart
  +--> orders
  +--> payments
  +--> notifications
  +--> search
```

This diagram expresses dependency direction, not permission to import every app into every other app.

### Rules

- `apps.common` must not import domain models.
- Domain apps may use common exceptions, pagination, and utilities.
- Common code must not depend on the current request's business-specific state.
- Avoid circular imports.
- Prefer standard Django app registration and lazy model references where applicable.
- Put cross-application workflows in an appropriate orchestration service rather than common.
- Keep global configuration in `config/settings/`.

---

## 14. Testing Strategy

Test every implemented shared component.

### Exception tests

Verify:

- Expected errors retain correct status codes.
- Validation details are preserved.
- Unexpected exceptions do not expose internal information.
- Logging does not include secrets.

### Pagination tests

Verify:

- Default page size.
- Maximum page size.
- Invalid pagination parameters.
- Deterministic ordering.
- No unauthorized records are exposed by shared pagination behavior.

### Validator tests

Verify valid and invalid values, boundary conditions, and malformed inputs.

### Health endpoint tests

Verify:

- Liveness does not depend on database availability.
- Readiness behaves correctly when required dependencies are available.
- Readiness fails safely when required dependencies are unavailable.
- Responses reveal no credentials or infrastructure details.
- Dependency checks use bounded operations.

### Middleware tests

If implemented, verify:

- Correlation identifiers are generated or validated correctly.
- Malformed identifiers are handled safely.
- Headers are applied consistently.
- Exceptions are not swallowed.
- Sensitive request information is not logged.

### Response tests

If a shared response convention is adopted, verify its success, error, pagination, and validation formats.

Tests must use isolated test configuration and must not access or mutate production Supabase data.

---

## 15. Security Requirements

The common app must:

- Avoid exposing internal exception details in production.
- Preserve correct HTTP status codes.
- Never bypass authentication or permission checks.
- Avoid logging sensitive request information.
- Restrict health responses to minimal operational information.
- Prevent unbounded database operations in health checks.
- Validate any externally supplied correlation identifier.
- Avoid dynamic execution, unsafe deserialization, or arbitrary file access.
- Use only the minimum functionality required for each shared concern.

Security settings such as HTTPS, HSTS, trusted hosts, cookies, CORS, CSRF, and secret management belong in the project-wide settings and deployment configuration rather than in common utilities.

---

## 16. Implementation Order

Implement the common app in the following order:

1. Inspect existing shared utilities, settings, exception handling, and URL routing.
2. Identify which infrastructure concerns are actually shared.
3. Decide and document the API response convention.
4. Establish exception-handling behavior.
5. Configure reusable pagination if needed.
6. Implement shared validators only where built-in validators are insufficient.
7. Implement liveness and readiness endpoints.
8. Add request-correlation middleware only if justified.
9. Add other utilities only when a concrete shared use case exists.
10. Add focused tests for every implemented component.
11. Mount the common URLs in the root URL configuration.
12. Verify OpenAPI behavior where endpoints are documented.
13. Run Ruff, Django checks, production checks, migration consistency checks, and the test suite.
14. Update `common_api.md` with all implemented public endpoints.

Do not run migrations against Supabase without explicit approval.

---

## 17. Definition of Done

The common app is considered implemented when:

- [ ] Its responsibilities and dependency boundaries are respected.
- [ ] No domain-specific business logic has been placed in common.
- [ ] Shared exceptions behave consistently.
- [ ] Response formatting is consistent with the documented project convention.
- [ ] Pagination and validators are tested if implemented.
- [ ] Liveness and readiness endpoints behave as documented.
- [ ] Health responses expose no secrets or internal infrastructure details.
- [ ] Middleware is implemented only if justified and is tested.
- [ ] Common utilities have clear consumers and documented behavior.
- [ ] All public endpoints are documented in `common_api.md`.
- [ ] Ruff linting and formatting checks pass.
- [ ] Django development checks pass.
- [ ] Production configuration checks pass with valid synthetic settings.
- [ ] Migration consistency checks pass.
- [ ] The full test suite passes.
- [ ] No secrets or unrelated files have been introduced.
- [ ] No database migrations, pushes, or deployments were performed without approval.

---

## 18. Instructions for AI Coding Agents

When implementing this specification:

1. Read this document before changing `apps.common`.
2. Inspect the existing project and avoid overwriting working code blindly.
3. Reuse Django and DRF functionality instead of creating unnecessary abstractions.
4. Keep common independent of business-domain models and workflows.
5. Do not create empty files simply to match the directory tree.
6. Implement and test actual behavior.
7. Update `common_api.md` whenever public endpoints change.
8. Run the project checks and report actual results.
9. Do not run migrations against Supabase, push commits, or deploy without explicit approval.

**This document defines the architectural contract for `apps.common`.** The separate `common_api.md` document must define the exact routes, methods, authentication requirements, response formats, and error behavior of its operational endpoints.