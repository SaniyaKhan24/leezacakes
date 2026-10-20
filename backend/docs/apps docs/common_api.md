# Common App — API Specification

**Project:** Leeza Cakes  
**Django application:** `apps.common`  
**API version:** v1  
**Status:** Specification defined; implementation pending  
**Related document:** `common_structure.md`

---

## 1. Purpose

The common API provides minimal operational endpoints used by deployment platforms, monitoring systems, and infrastructure checks.

It does not expose business functionality. Account management, products, cart, orders, payments, notifications, and search each have their own API specifications.

### Endpoints

| Method | Endpoint | Authentication | Purpose |
|---|---|---|---|
| `GET` | `/health/live/` | Public or infrastructure-accessible | Confirm the application process is alive |
| `GET` | `/health/ready/` | Public or infrastructure-accessible | Confirm essential dependencies are available |

These routes should be mounted at the project root, independently of the versioned business API prefix. The exact route placement must be consistent with `config/urls.py`.

Recommended development URLs:

- `http://localhost:8000/health/live/`
- `http://localhost:8000/health/ready/`

Do not add public endpoints for exceptions, validators, pagination, constants, or other internal utilities.

---

## 2. `GET /health/live/`

**Purpose:** Determine whether the Django process is alive and able to serve requests.

**Authentication:** No application authentication required when the deployment platform needs unauthenticated probes. Restrict access at the network or proxy layer if required by the hosting environment.

**Database dependency:** None.

### Behavior

The endpoint must:

1. Return quickly without accessing the database.
2. Avoid calling email, payment, storage, or other external providers.
3. Avoid expensive computation.
4. Return a minimal response.
5. Never disclose environment variables, credentials, internal exception details, or infrastructure information.

### Success response

HTTP `200 OK`

```json
{
  "status": "ok"
}
```

### Failure behavior

The endpoint should not return a false failure merely because an external dependency is unavailable. If the process can serve the request, liveness should generally remain successful.

A process-level failure may prevent the endpoint from responding at all; the hosting platform should detect that condition through its probe timeout.

### Implementation requirements

- Use a lightweight Django view.
- Return JSON using Django or DRF response primitives.
- Do not query PostgreSQL.
- Do not expose a version number, deployment environment, hostname, or internal diagnostics unless there is a separately approved requirement.
- Do not include this endpoint in business authentication throttling.

### Tests

- The endpoint returns HTTP `200`.
- The response contains only the documented minimal status.
- The endpoint succeeds when database access is unavailable.
- The endpoint does not disclose environment configuration.

---

## 3. `GET /health/ready/`

**Purpose:** Determine whether the application can serve requests that depend on essential infrastructure.

**Authentication:** No application authentication required when the deployment platform needs unauthenticated probes. Restrict access at the network or proxy layer where appropriate.

**Database dependency:** Yes, if PostgreSQL is required for normal application operations.

### Behavior

The endpoint must:

1. Check the availability of essential dependencies according to the deployment readiness policy.
2. Use bounded, lightweight checks.
3. Avoid expensive database queries.
4. Avoid exposing connection details or diagnostic information publicly.
5. Return a non-success HTTP status when an essential dependency is unavailable.
6. Avoid checking optional integrations unless the business policy explicitly requires them for readiness.

For the initial Leeza Cakes backend, PostgreSQL is the primary dependency to evaluate. Email delivery and payment-provider availability should not normally make the entire application unready.

### Success response

HTTP `200 OK`

```json
{
  "status": "ok"
}
```

### Dependency unavailable response

Return an appropriate non-success status, normally HTTP `503 Service Unavailable`.

```json
{
  "status": "unavailable"
}
```

Do not include raw database errors, hostnames, credentials, SQL statements, or stack traces.

### Database-check requirements

- Use the configured Django database connection.
- Keep the check lightweight.
- Avoid creating, updating, or deleting records.
- Do not run migrations.
- Do not access the database repeatedly in a tight retry loop.
- Apply a suitable timeout at the database-driver or infrastructure level.
- Ensure monitoring frequency is reasonable.
- Log unexpected failures safely on the server if operational logging is configured.

### Supabase considerations

The readiness check must use the existing Supabase PostgreSQL configuration. It must not replace the configured database with SQLite, create a new database, or alter any schema.

The check should perform only a harmless connectivity query. It must not test readiness by attempting to create tables or write test data.

### Tests

- Returns HTTP `200` when the required database dependency is available.
- Returns HTTP `503` when the required dependency is unavailable.
- Does not expose internal database error details.
- Does not modify database data.
- Does not require email or payment-provider availability.
- Uses bounded operations and avoids repeated connection attempts.

---

## 4. Routing and URL Configuration

The endpoints must be registered through `apps.common.urls` and included in the root URL configuration.

Recommended route structure:

```text
config.urls
├── health/live/       → apps.common
├── health/ready/      → apps.common
└── api/v1/
    ├── accounts/      → apps.accounts
    ├── catalog/       → apps.catalog
    ├── customization/ → apps.customization
    ├── cart/           → apps.cart
    ├── orders/         → apps.orders
    ├── payments/       → apps.payments
    ├── notifications/  → apps.notifications
    └── search/         → apps.search
```

This is the intended routing structure; the business endpoints must be added when their respective apps are implemented.

Do not mount health endpoints twice or create conflicting URL patterns.

---

## 5. Authentication and Permissions

Health endpoints are operational endpoints rather than customer-facing business APIs.

The default policy is:

- Liveness is accessible to the configured health probe.
- Readiness is accessible to the configured health probe.
- Neither endpoint returns sensitive diagnostics.
- Neither endpoint exposes account, product, order, or payment data.

If the deployment requires authenticated probes or network restrictions, configure them at the appropriate infrastructure layer and document the resulting behavior.

Do not make internal debugging or detailed dependency-status endpoints public.

---

## 6. HTTP and Error Semantics

| Scenario | Expected status |
|---|---|
| Application alive | `200 OK` |
| Required dependencies ready | `200 OK` |
| Required dependency unavailable | `503 Service Unavailable` |
| Unexpected request-handling failure | Appropriate server error without internal details |

The exact response schema must remain minimal and consistent.

Health responses should not include arbitrary exception messages or dynamically generated diagnostic objects.

---

## 7. API Documentation

Health endpoints are operational endpoints. Document them in the project's API documentation where useful, but do not expose sensitive infrastructure information through OpenAPI.

If included in the generated OpenAPI schema:

- Give each endpoint a clear summary and description.
- Document the success response.
- Document the unavailable response for readiness.
- Avoid documenting internal exception details.
- Ensure the schema matches the actual implementation.

---

## 8. Testing Requirements

Implement automated tests for both endpoints.

At minimum:

- Liveness returns the expected status and response body.
- Liveness does not access the database.
- Readiness succeeds with the required dependency available.
- Readiness fails safely when PostgreSQL is unavailable.
- Readiness returns no internal diagnostic details.
- Neither endpoint mutates data.
- URL routing resolves to the correct views.
- Response formats match this specification.

Tests must use isolated test settings and test infrastructure. They must not rely on the live Supabase database.

---

## 9. Out of Scope

The following do not belong in the common HTTP API:

- Generic exception creation or inspection endpoints.
- Arbitrary database-query endpoints.
- Public configuration endpoints.
- Environment-variable inspection endpoints.
- Debug or stack-trace endpoints.
- Generic file-upload endpoints.
- Shared utility execution endpoints.
- Customer or staff management endpoints.
- Catalogue, cart, order, or payment endpoints.
- Public service-status details that expose internal architecture.

Shared exceptions, pagination, validators, response helpers, and middleware should be implemented as internal Python components when required.

---

## 10. Definition of Done

The common API is complete when:

- [ ] Both health routes are registered exactly once.
- [ ] Liveness does not depend on external services.
- [ ] Readiness checks only the dependencies required by the documented policy.
- [ ] Database checks are read-only and bounded.
- [ ] No secrets or internal diagnostics are exposed.
- [ ] Both endpoints have automated tests.
- [ ] Routing tests pass.
- [ ] API documentation matches actual endpoint behavior.
- [ ] Ruff checks pass.
- [ ] Django checks pass.
- [ ] The full test suite passes.
- [ ] No migrations, production database changes, pushes, or deployments were performed without approval.

---

## 11. Instructions for AI Coding Agents

When implementing this specification:

1. Read `common_structure.md` first.
2. Inspect the current root URL configuration and health implementation before editing.
3. Reuse existing views and routes instead of creating duplicates.
4. Implement only the documented operational endpoints.
5. Keep shared utilities internal unless there is a concrete HTTP use case.
6. Do not expose environment variables, database errors, or internal infrastructure information.
7. Write tests for the actual behavior.
8. Update this document if the endpoint contract changes.
9. Run the project checks and report actual results.
10. Do not run migrations against Supabase, push commits, or deploy without explicit approval.

**This document defines the intended public HTTP contract for `apps.common`.** The architecture, implementation, and tests must agree with this specification.