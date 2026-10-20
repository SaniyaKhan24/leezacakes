# Accounts App — API Specification

**Project:** Leeza Cakes  
**Application:** `apps.accounts`  
**API version:** v1  
**Base path:** `/api/v1/accounts/`  
**Status:** Specification defined; implementation pending  
**Related document:** `accounts_structure.md`

---

## 1. API Conventions

### 1.1 Base URL

Development base URL:

`http://localhost:8000/api/v1/accounts/`

Production base URL must be configured through the deployment environment. Do not hard-code a production domain.

All endpoints use JSON request and response bodies unless explicitly stated otherwise.

### 1.2 Response conventions

Successful responses should use consistent JSON structures. For example:

```json
{
  "data": {
    "id": "uuid",
    "email": "customer@example.com"
  }
}
```

Paginated endpoints may use the project's standardized pagination format. The implementation must choose one response convention consistently and document it.

Error responses should follow a predictable structure, preferably compatible with DRF validation errors:

```json
{
  "detail": "The request could not be completed."
}
```

Field-validation errors may include field-specific messages. Never return stack traces, SQL errors, secrets, password hashes, or raw authentication tokens in error messages.

### 1.3 Authentication

Use the authentication strategy selected in `accounts_structure.md`.

The preferred implementation is JWT authentication with a maintained, compatible package, short-lived access tokens, refresh-token rotation, and refresh-token revocation where appropriate.

The exact request and response formats for token operations must match the selected library and configured cookie strategy. Do not implement an incompatible custom token protocol.

For endpoints that require authentication, reject anonymous requests with HTTP `401 Unauthorized` where appropriate.

For authenticated users who lack permission, return HTTP `403 Forbidden`, or use a consistent `404 Not Found` policy when deliberately concealing another user's resource.

### 1.4 Permissions

- Public endpoints must be explicitly marked public.
- Private endpoints require authentication.
- Customers may access only their own account resources.
- Staff operations require explicit Django permissions.
- Public registration must never grant administrative privileges.
- Client-supplied user IDs must never override the authenticated identity.

### 1.5 Common HTTP status codes

| Status | Meaning |
|---|---|
| `200 OK` | Successful read or operation |
| `201 Created` | Resource created |
| `202 Accepted` | Request accepted for asynchronous processing, where applicable |
| `204 No Content` | Successful operation without a response body |
| `400 Bad Request` | Invalid input or invalid operation |
| `401 Unauthorized` | Missing or invalid authentication |
| `403 Forbidden` | Authenticated user lacks permission |
| `404 Not Found` | Resource does not exist or is intentionally concealed |
| `409 Conflict` | State or uniqueness conflict where this response is appropriate |
| `429 Too Many Requests` | Rate limit exceeded |
| `500 Internal Server Error` | Unexpected server failure, with no internal details exposed |

Use status codes consistently and document deviations.

---

## 2. Endpoint Inventory

The following endpoints define the intended customer-facing accounts API. Implement them according to the product requirements and authentication strategy. Do not create duplicate endpoints for functionality already supplied by an adopted authentication library unless a deliberate API contract requires an adapter.

| Method | Endpoint | Authentication | Purpose |
|---|---|---|---|
| `POST` | `/register/` | Public | Create a customer account |
| `POST` | `/login/` | Public | Authenticate a customer |
| `POST` | `/logout/` | Authenticated | End the authentication session or revoke refresh credentials |
| `POST` | `/token/refresh/` | Refresh credential | Obtain a new access token |
| `GET` | `/me/` | Authenticated | Retrieve the current customer's profile |
| `PATCH` | `/me/` | Authenticated | Update permitted profile fields |
| `POST` | `/password/change/` | Authenticated | Change the current password |
| `POST` | `/password/reset/` | Public | Request a password-reset email |
| `POST` | `/password/reset/confirm/` | Public with reset challenge | Set a new password |
| `POST` | `/email/verification/request/` | Public or authenticated, depending on policy | Request email verification |
| `POST` | `/email/verification/confirm/` | Public with verification challenge | Verify an email address |
| `GET` | `/addresses/` | Authenticated | List the customer's saved addresses |
| `POST` | `/addresses/` | Authenticated | Create a saved address |
| `GET` | `/addresses/{address_id}/` | Authenticated | Retrieve an owned address |
| `PATCH` | `/addresses/{address_id}/` | Authenticated | Update an owned address |
| `DELETE` | `/addresses/{address_id}/` | Authenticated | Delete an owned address |
| `POST` | `/addresses/{address_id}/set-default/` | Authenticated | Make an owned address the default |

The API may be extended when a concrete requirement arises. Do not add public account enumeration endpoints.

---

## 3. Registration

### `POST /register/`

**Authentication:** Public  
**Purpose:** Create a new customer account.

#### Request

```json
{
  "email": "customer@example.com",
  "password": "Example-password-123!",
  "password_confirm": "Example-password-123!",
  "first_name": "Aisha",
  "last_name": "Khan",
  "phone_number": "+919876543210"
}
```

`phone_number` is optional if the product does not require it. Do not accept administrative fields such as `is_staff`, `is_superuser`, `is_active`, or `is_email_verified`.

#### Behavior

1. Validate and normalize the email address.
2. Validate the password using Django's configured password validators.
3. Confirm the two password values match.
4. Create the account using the user manager.
5. Apply the agreed email-verification and activation policy.
6. Initiate email verification through the notifications integration if required.
7. Return a safe representation of the new account.

Do not send a verification email before the account transaction commits. Use an appropriate post-commit or durable task mechanism.

#### Success

`201 Created`

```json
{
  "data": {
    "id": "uuid",
    "email": "customer@example.com",
    "first_name": "Aisha",
    "last_name": "Khan",
    "is_email_verified": false
  }
}
```

The verification value shown here is an example; actual behavior must follow the selected account activation policy.

#### Validation errors

- `400 Bad Request` for invalid fields or mismatched passwords.
- Duplicate email handling must be consistent and must not expose internal database errors.
- Do not return a password or password hash.

**Security:** Rate-limit registration. Decide whether duplicate email responses should reveal account existence; for privacy-sensitive flows, use a generic response policy.

---

## 4. Login

### `POST /login/`

**Authentication:** Public  
**Purpose:** Authenticate a customer.

#### Request

```json
{
  "email": "customer@example.com",
  "password": "Example-password-123!"
}
```

#### Behavior

- Authenticate using Django's configured authentication backend.
- Enforce account activation and verification rules.
- Apply throttling.
- Return credentials according to the chosen JWT or session strategy.
- Update last-login information through the appropriate framework mechanism.
- Record security-relevant events without logging passwords or tokens.

#### Success

`200 OK`

For a bearer-token strategy, the response shape may resemble:

```json
{
  "data": {
    "access": "<access-token>",
    "refresh": "<refresh-token>",
    "user": {
      "id": "uuid",
      "email": "customer@example.com",
      "first_name": "Aisha",
      "last_name": "Khan"
    }
  }
}
```

This is illustrative, not a requirement to build a custom token format. If refresh credentials are stored in secure cookies, do not also expose them in the JSON body.

#### Errors

- `400 Bad Request` for malformed input.
- `401 Unauthorized` for invalid credentials.
- A consistent error response for inactive or unverified accounts according to the security policy.
- `429 Too Many Requests` when throttled.

Never reveal whether a specific email address exists.

---

## 5. Logout

### `POST /logout/`

**Authentication:** Authenticated  
**Purpose:** End the current authentication session.

#### Request

For JWT authentication, provide the refresh credential through the selected secure mechanism. For cookie-based refresh authentication, use the configured cookie and CSRF protections.

#### Behavior

- Revoke or blacklist the refresh credential where supported.
- Clear authentication cookies where applicable.
- Apply the documented access-token invalidation policy.
- Treat repeated logout attempts predictably.

#### Success

`204 No Content`

Do not claim that an access token has been immediately revoked unless the implementation actually supports immediate revocation.

---

## 6. Refresh Access Token

### `POST /token/refresh/`

**Authentication:** Valid refresh credential  
**Purpose:** Obtain a replacement access token.

The request and response must match the selected authentication library and cookie policy.

For body-based refresh authentication, the request may contain:

```json
{
  "refresh": "<refresh-token>"
}
```

#### Behavior

- Validate the refresh credential.
- Reject expired, invalid, or revoked credentials.
- Rotate refresh credentials if rotation is enabled.
- Blacklist the previous refresh credential when supported and configured.
- Apply the documented reuse-detection policy.

Do not log token values. Rate-limit this endpoint appropriately.

---

## 7. Current Customer Profile

### `GET /me/`

**Authentication:** Required  
**Purpose:** Retrieve the authenticated customer's own profile.

#### Success

`200 OK`

```json
{
  "data": {
    "id": "uuid",
    "email": "customer@example.com",
    "first_name": "Aisha",
    "last_name": "Khan",
    "phone_number": "+919876543210",
    "is_email_verified": true,
    "date_joined": "2026-10-19T08:00:00Z"
  }
}
```

Return only fields intended for the customer-facing API. Do not expose password hashes, staff flags, superuser flags, token data, or internal security metadata.

### `PATCH /me/`

**Authentication:** Required  
**Purpose:** Update permitted customer profile fields.

#### Request

```json
{
  "first_name": "Aisha",
  "last_name": "Khan",
  "phone_number": "+919876543210"
}
```

#### Rules

- Only explicitly allowed fields may be updated.
- Do not permit changes to `id`, administrative flags, account activation state, verification flags, password hashes, or other privileged fields.
- Email changes, if supported, must use a dedicated verified change-email flow.
- Validate phone numbers and normalize them consistently.
- Do not permit mass assignment through arbitrary JSON fields.

#### Success

`200 OK`, returning the updated public profile representation.

---

## 8. Change Password

### `POST /password/change/`

**Authentication:** Required  
**Purpose:** Change the authenticated customer's password.

#### Request

```json
{
  "current_password": "Current-password-123!",
  "new_password": "New-password-456!",
  "new_password_confirm": "New-password-456!"
}
```

#### Behavior

- Verify the current password.
- Validate the new password using Django's password validators.
- Ensure the new password values match.
- Save the password using Django's password API.
- Apply the session and token invalidation policy.
- Notify the customer through the notification integration where required.

#### Success

`200 OK`

```json
{
  "detail": "Password changed successfully."
}
```

Return `400 Bad Request` for validation failures and a generic authentication-related error for an incorrect current password.

---

## 9. Request Password Reset

### `POST /password/reset/`

**Authentication:** Public  
**Purpose:** Request a password-reset email.

#### Request

```json
{
  "email": "customer@example.com"
}
```

#### Behavior

- Return the same public response regardless of whether the account exists.
- Generate a secure, time-limited reset challenge for an eligible account.
- Deliver the reset link through the notifications integration.
- Apply rate limiting.
- Avoid disclosing account status through timing or response differences where practical.

#### Success

`200 OK`

```json
{
  "detail": "If an eligible account exists, password-reset instructions will be sent."
}
```

Do not return a reset token in the response.

---

## 10. Confirm Password Reset

### `POST /password/reset/confirm/`

**Authentication:** Public with a valid reset challenge  
**Purpose:** Set a new password using a reset challenge.

#### Request

```json
{
  "uid": "<encoded-user-identifier>",
  "token": "<password-reset-token>",
  "new_password": "New-password-456!",
  "new_password_confirm": "New-password-456!"
}
```

The exact challenge format must follow the selected Django password-reset implementation.

#### Behavior

- Validate the user identifier and reset token.
- Enforce token expiry and single-use behavior.
- Validate the new password.
- Update the password securely.
- Invalidate the reset challenge.
- Revoke applicable sessions or refresh credentials.
- Notify the customer of the completed reset.

#### Success

`200 OK`

```json
{
  "detail": "Password has been reset successfully."
}
```

Invalid, expired, or reused challenges must be rejected without exposing internal details.

---

## 11. Request Email Verification

### `POST /email/verification/request/`

**Authentication:** Depends on the selected policy. Prefer authenticated access for logged-in customers and a generic response for public recovery-style requests.

**Purpose:** Send or resend an email verification challenge.

#### Request

```json
{
  "email": "customer@example.com"
}
```

If the customer is authenticated and verification is tied to the current account, prefer deriving the email from the authenticated user rather than trusting the supplied address.

#### Behavior

- Check the account and verification state.
- Generate a secure, time-limited verification challenge.
- Invalidate or supersede previous challenges according to the documented policy.
- Deliver the verification link through the notification integration.
- Rate-limit repeated requests.

#### Success

`200 OK`

```json
{
  "detail": "If verification is required, instructions will be sent."
}
```

Do not reveal whether an arbitrary email address is registered.

---

## 12. Confirm Email Verification

### `POST /email/verification/confirm/`

**Authentication:** Public with a valid verification challenge, or authenticated if required by the selected policy.

#### Request

```json
{
  "uid": "<encoded-user-identifier>",
  "token": "<verification-token>"
}
```

#### Behavior

- Validate the challenge, purpose, and expiry.
- Verify that the challenge belongs to the intended account.
- Consume the challenge exactly once.
- Update the email verification state transactionally.
- Apply the account activation policy.
- Do not grant elevated permissions.

#### Success

`200 OK`

```json
{
  "data": {
    "is_email_verified": true
  }
}
```

Invalid, expired, and reused tokens must be rejected. Never log raw verification tokens.

---

## 13. List Saved Addresses

### `GET /addresses/`

**Authentication:** Required  
**Purpose:** List the authenticated customer's saved addresses.

#### Behavior

- Query only addresses belonging to the authenticated customer.
- Use a deterministic ordering.
- Apply pagination if the project requires it.
- Do not return addresses belonging to other customers.

#### Success

`200 OK`

```json
{
  "data": [
    {
      "id": "uuid",
      "label": "Home",
      "recipient_name": "Aisha Khan",
      "phone_number": "+919876543210",
      "address_line_1": "Example Street",
      "address_line_2": null,
      "locality": "Example Area",
      "city": "Pune",
      "state": "Maharashtra",
      "postal_code": "411001",
      "country_code": "IN",
      "is_default": true
    }
  ]
}
```

---

## 14. Create Saved Address

### `POST /addresses/`

**Authentication:** Required  
**Purpose:** Save a customer address.

#### Request

```json
{
  "label": "Home",
  "recipient_name": "Aisha Khan",
  "phone_number": "+919876543210",
  "address_line_1": "Example Street",
  "address_line_2": null,
  "locality": "Example Area",
  "city": "Pune",
  "state": "Maharashtra",
  "postal_code": "411001",
  "country_code": "IN",
  "is_default": true
}
```

#### Rules

- The owner must be derived from the authenticated user.
- Ignore or reject any client-supplied `user` field.
- Validate required fields and country/postal-code rules.
- Enforce the single-default-address invariant.
- If making the new address the default, clear the previous default within the same transaction.

#### Success

`201 Created`, returning the created address.

---

## 15. Retrieve Saved Address

### `GET /addresses/{address_id}/`

**Authentication:** Required  
**Purpose:** Retrieve one address owned by the authenticated customer.

#### Behavior

Retrieve the address using both its identifier and authenticated owner.

Do not retrieve an unrestricted address and rely on the frontend to enforce ownership.

#### Success

`200 OK`, returning the address representation.

For another customer's address, use the documented concealment policy, typically `404 Not Found`.

---

## 16. Update Saved Address

### `PATCH /addresses/{address_id}/`

**Authentication:** Required  
**Purpose:** Update an owned saved address.

#### Request

Accept only explicitly permitted address fields. For example:

```json
{
  "label": "Work",
  "city": "Pune",
  "is_default": false
}
```

#### Rules

- Verify ownership before modifying the resource.
- Reject unauthorized fields such as `user`.
- Validate the resulting address, including unchanged fields where cross-field validation is required.
- If default status changes, enforce the invariant transactionally.
- Do not modify existing order-address snapshots.

#### Success

`200 OK`, returning the updated address.

---

## 17. Delete Saved Address

### `DELETE /addresses/{address_id}/`

**Authentication:** Required  
**Purpose:** Delete an owned saved address.

#### Behavior

- Verify ownership.
- Apply the documented deletion policy.
- Do not delete or alter historical order-address snapshots.
- If the default address is deleted, leave the customer with no default address unless the product explicitly defines an alternative behavior.

#### Success

`204 No Content`

---

## 18. Set Default Address

### `POST /addresses/{address_id}/set-default/`

**Authentication:** Required  
**Purpose:** Mark an owned address as the customer's default saved address.

#### Behavior

- Verify ownership.
- Execute the default change atomically.
- Clear the previous default.
- Enforce the single-default-address invariant under concurrent requests.
- Return the updated address.

#### Success

`200 OK`

```json
{
  "data": {
    "id": "uuid",
    "is_default": true
  }
}
```

---

## 19. Validation and Error Handling

All serializers must define explicit allowed fields and validation rules.

Common validation scenarios include:

- Missing required fields.
- Invalid email format.
- Invalid phone number.
- Password policy failure.
- Mismatched password confirmation.
- Duplicate email.
- Invalid or expired verification challenge.
- Invalid or expired reset challenge.
- Invalid address fields.
- Attempted modification of restricted fields.
- Invalid authentication credentials.
- Resource ownership violations.

Use DRF validation errors consistently. Do not expose database exceptions, tracebacks, raw tokens, or internal object representations.

A representative field-validation response is:

```json
{
  "email": [
    "Enter a valid email address."
  ]
}
```

The precise error messages may differ, but the response format must remain consistent and must not disclose sensitive account information.

---

## 20. Rate Limiting

Apply stricter throttling to security-sensitive endpoints:

- Registration.
- Login.
- Token refresh.
- Password-reset requests.
- Password-reset confirmation.
- Email-verification requests.
- Email-verification confirmation.

Configure rates through settings rather than scattering hard-coded limits across views.

Production throttling must use a shared cache or another distributed mechanism when multiple application instances are deployed. Local in-memory throttling is not sufficient for distributed production enforcement.

Rate limits should be tested, documented, and adjusted using observed traffic and abuse patterns.

---

## 21. OpenAPI and Documentation

Every implemented endpoint must be included in the generated OpenAPI schema.

Document:

- HTTP method and path.
- Summary and detailed description.
- Authentication requirements.
- Permission requirements.
- Request schema.
- Success response schema.
- Validation and authentication errors.
- Rate-limiting behavior where applicable.

Use the project's configured `drf-spectacular` setup. Swagger and Scalar must render the generated schema rather than maintain separate, manually written API definitions.

Do not document unimplemented endpoints as if they are available in production. Clearly distinguish planned endpoints from implemented ones.

---

## 22. Required API Tests

Each endpoint must have tests covering its normal behavior and security boundaries.

At minimum:

- Registration creates a user with a hashed password.
- Duplicate registration is handled safely.
- Public registration cannot assign administrative privileges.
- Login rejects invalid credentials.
- Inactive and unverified account policies are enforced.
- Logout and refresh follow the configured token policy.
- Profile endpoints expose only permitted fields.
- Password change requires the current password.
- Password recovery does not reveal account existence.
- Reset and verification challenges expire and cannot be reused.
- Address endpoints enforce ownership for every operation.
- Concurrent default-address updates preserve the invariant.
- Sensitive tokens and password fields never appear in API responses.
- Throttling is applied to sensitive endpoints.
- All implemented endpoints appear in the OpenAPI schema.

Tests must use isolated test data and must not depend on the live Supabase database.

---

## 23. Implementation Rules for AI Coding Agents

When implementing this API:

1. Read `accounts_structure.md` before modifying the application.
2. Inspect the actual settings, dependencies, authentication configuration, and migration history.
3. Implement the selected authentication strategy consistently.
4. Do not invent a second user model or bypass Django's user manager.
5. Do not add business logic belonging to cart, orders, payments, catalogue, or notifications.
6. Enforce permissions and ownership in backend queries and operations.
7. Use explicit serializers and service-layer operations where appropriate.
8. Add tests for every endpoint and security-sensitive behavior.
9. Update this document whenever endpoint behavior changes.
10. Run the project checks and report actual results.
11. Do not execute migrations against Supabase, push commits, or deploy without explicit approval.

**Definition of completion:** the documented endpoints are implemented, tested, secured according to the selected authentication strategy, and included in the generated OpenAPI schema. The existence of this document alone does not mean the endpoints have been implemented.