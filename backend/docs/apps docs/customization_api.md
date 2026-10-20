# Customization API — Endpoint Specification

**Project:** Leeza Cakes  
**Django app:** `apps.customization`  
**Base path:** `/api/v1/customization/`  
**Status:** API contract specification  
**Audience:** Backend developers, frontend developers, and AI coding agents

## 1. Purpose

This document defines the API contract for retrieving available cake customization options, retrieving product-specific choices, validating customer selections, and managing customization configurations.

The API must support product-specific customization while keeping product identity and base pricing in `apps.catalog`, cart state in `apps.cart`, and historical order records in `apps.orders`.

All pricing and selection validation must be performed on the server. The frontend must never be trusted to determine the authoritative customization price.

## 2. API Conventions

- Use JSON for normal requests and responses.
- Use the existing API versioning, pagination, exception handling, and response conventions.
- Use the configured authentication mechanism and explicit permissions for administrative endpoints.
- Use stable identifiers for options and choices.
- Return monetary amounts as decimal strings, with an explicit currency code.
- Do not expose inactive or ineligible options through public endpoints.
- Do not introduce a second response envelope if `apps.common` already defines one.
- Document all implemented endpoints in the project's existing OpenAPI schema.

Base URL example:

`http://localhost:8000/api/v1/customization/`

## 3. Public Endpoints

### 3.1 Retrieve customization options for a product

`GET /api/v1/customization/products/{product_slug}/options/`

**Purpose:** Return the customization options currently available for a published product.

**Authentication:** Not required.

**Success:** `200 OK`

**Not found:** `404 Not Found` when the product does not exist or is not publicly accessible.

**Response fields:**

- Option ID.
- Option name and slug.
- Description, if available.
- Input type, such as single choice, multiple choice, or text.
- Whether a selection is required.
- Minimum and maximum selections, when applicable.
- Available choices.
- Product-specific price adjustments, where applicable.
- Display ordering.

Only return options and choices that are active and enabled for the requested product.

**Example response:**

```json
{
  "product": {
    "slug": "chocolate-truffle-cake",
    "name": "Chocolate Truffle Cake"
  },
  "options": [
    {
      "id": 11,
      "name": "Flavour",
      "slug": "flavour",
      "input_type": "single_choice",
      "is_required": true,
      "min_selections": 1,
      "max_selections": 1,
      "choices": [
        {
          "id": 101,
          "name": "Chocolate",
          "price_adjustment": "0.00",
          "currency": "INR"
        },
        {
          "id": 102,
          "name": "Red Velvet",
          "price_adjustment": "100.00",
          "currency": "INR"
        }
      ]
    },
    {
      "id": 12,
      "name": "Cake Message",
      "slug": "cake-message",
      "input_type": "text",
      "is_required": false,
      "max_length": 80
    }
  ]
}
```

The example is illustrative. Field names and values must match the implemented models and agreed business rules.

Do not return all globally defined choices if only a subset is enabled for the product.

### 3.2 Retrieve choices for a product option

`GET /api/v1/customization/products/{product_slug}/options/{option_id}/choices/`

**Purpose:** Return the eligible choices for one customization option on a product.

**Authentication:** Not required.

**Success:** `200 OK`

**Not found:** `404 Not Found` if the product, option, or product-option association is unavailable publicly.

This endpoint is optional when the options endpoint already includes all choices. Implement it only if separate choice loading materially benefits the frontend or the catalogue contains enough choices to justify it.

The endpoint must verify that the requested option is associated with the specified product. A globally valid option ID must not grant access to choices for another product.

## 4. Validate Customer Selections

### 4.1 Validate customization selections

`POST /api/v1/customization/products/{product_slug}/validate/`

**Purpose:** Validate a proposed set of customization selections before adding them to the cart.

**Authentication:** Not required for validation of public product options, unless the workflow requires an authenticated draft or private upload.

**Request body:**

```json
{
  "selections": [
    {
      "option_id": 11,
      "choice_ids": [101]
    },
    {
      "option_id": 12,
      "text_value": "Happy Birthday!"
    }
  ]
}
```

For text-based options, use `text_value`. For choice-based options, use `choice_ids`. Do not accept both unless the option explicitly supports that behavior.

**Validation requirements:**

1. The product exists and is eligible for the requested workflow.
2. Every submitted option is enabled for that product.
3. Every submitted choice belongs to the relevant option and is enabled for that product.
4. Required options have valid selections.
5. Single-choice options contain no more than one choice.
6. Multiple-choice options respect minimum and maximum selection limits.
7. Duplicate choices are rejected where not permitted.
8. Text values satisfy configured length and content constraints.
9. Prices are derived from trusted server-side records.
10. Inactive, archived, or otherwise ineligible selections are rejected.
11. Variant and size pricing are not double-counted.
12. Unsupported fields are rejected or safely ignored according to the project's established serializer policy.

**Success:** `200 OK`

**Example response:**

```json
{
  "valid": true,
  "product": {
    "slug": "chocolate-truffle-cake"
  },
  "selections": [
    {
      "option_id": 11,
      "option_name": "Flavour",
      "choice_id": 101,
      "choice_name": "Chocolate",
      "price_adjustment": "0.00",
      "currency": "INR"
    },
    {
      "option_id": 12,
      "option_name": "Cake Message",
      "text_value": "Happy Birthday!",
      "price_adjustment": "0.00",
      "currency": "INR"
    }
  ],
  "customization_total": "0.00",
  "currency": "INR"
}
```

The total shown here is illustrative. If the project distinguishes per-unit adjustments from per-item adjustments, the response must identify those semantics clearly.

**Invalid selection:** `400 Bad Request`

Example:

```json
{
  "error": {
    "code": "invalid_customization",
    "message": "One or more customization selections are invalid.",
    "details": {
      "selections": [
        "The selected choice is not available for this product."
      ]
    }
  }
}
```

Use the actual project-wide error format if one already exists.

**Important:** This endpoint is a validation convenience, not a purchase authorization or price guarantee. The cart must validate selections again when the item is added or updated and at relevant checkout boundaries.

If the cart already provides reliable validation and the frontend does not need a separate validation call, this endpoint may be omitted. Shared business validation must still exist in a reusable service.

## 5. Administrative Endpoints

All administrative endpoints require authentication and explicit catalogue/customization-management permissions. A normal authenticated customer must not be allowed to manage customization definitions.

### 5.1 List customization options

`GET /api/v1/customization/admin/options/`

**Purpose:** List options for administrative management, including inactive options.

**Permission:** Authorized customization staff.

**Optional query parameters:**

- `is_active`
- `input_type`
- `search`
- `page`
- `page_size`

Return a paginated response using the project's configured pagination conventions.

### 5.2 Create customization option

`POST /api/v1/customization/admin/options/`

**Permission:** Authorized customization staff.

**Request fields:**

- `name` — required.
- `slug` — required or generated according to the slug policy.
- `description` — optional.
- `input_type` — required.
- `is_active` — permitted only for authorized staff.
- `sort_order` — optional.

**Success:** `201 Created`

Validate uniqueness, supported input types, and any constraints associated with the selected input type.

### 5.3 Retrieve customization option

`GET /api/v1/customization/admin/options/{option_id}/`

**Permission:** Authorized customization staff.

Return the administrative representation, including the fields needed to manage the option.

### 5.4 Update customization option

`PATCH /api/v1/customization/admin/options/{option_id}/`

**Permission:** Authorized customization staff.

Allow partial updates of permitted fields. Validate changes against existing choices and product associations.

Changing an option's input type must not silently invalidate existing product configurations or historical orders.

### 5.5 Create a choice

`POST /api/v1/customization/admin/options/{option_id}/choices/`

**Permission:** Authorized customization staff.

**Request fields:**

- `name` — required.
- `slug` — required or generated according to the slug policy.
- `description` — optional.
- `is_active` — optional.
- `sort_order` — optional.

**Success:** `201 Created`

The choice must belong to the specified option.

### 5.6 Update a choice

`PATCH /api/v1/customization/admin/options/{option_id}/choices/{choice_id}/`

**Permission:** Authorized customization staff.

Verify that the choice belongs to the requested option. Reject invalid relationships and unsupported fields.

### 5.7 Configure customization for a product

`POST /api/v1/customization/admin/products/{product_id}/options/`

**Purpose:** Associate an existing customization option with a catalogue product.

**Permission:** Authorized customization staff.

**Example request:**

```json
{
  "option_id": 11,
  "is_required": true,
  "is_active": true,
  "min_selections": 1,
  "max_selections": 1,
  "sort_order": 1
}
```

**Success:** `201 Created`

Validate that the product and option exist and that a duplicate association is not created.

The exact fields must reflect the implemented `ProductCustomization` model. Omit fields not supported by the chosen input type.

### 5.8 Update product customization configuration

`PATCH /api/v1/customization/admin/products/{product_id}/options/{product_customization_id}/`

**Permission:** Authorized customization staff.

Allow changes to product-specific requirements, active status, and display ordering.

Verify that the configuration belongs to the specified product.

### 5.9 Configure available choices and pricing

`POST /api/v1/customization/admin/products/{product_id}/options/{product_customization_id}/choices/`

**Purpose:** Make a reusable choice available for a particular product customization and configure its applicable price adjustment.

**Permission:** Authorized customization staff.

**Example request:**

```json
{
  "choice_id": 102,
  "price_adjustment": "100.00",
  "is_active": true,
  "sort_order": 2
}
```

**Success:** `201 Created`

Validate:

- The product customization belongs to the requested product.
- The choice belongs to the specified customization option.
- The choice is not already associated with the same product customization.
- The price adjustment satisfies the documented pricing policy.
- The currency is consistent with the associated pricing configuration.

The example uses INR for illustration. Do not accept a client-supplied currency or adjustment without validating it against the server's configured pricing policy.

### 5.10 Update product-specific choice configuration

`PATCH /api/v1/customization/admin/products/{product_id}/options/{product_customization_id}/choices/{product_choice_id}/`

**Permission:** Authorized customization staff.

Allow updates to the supported price adjustment, active status, and ordering fields.

Verify all resource relationships before updating.

### 5.11 Deactivate options or choices

Use the relevant update endpoint to set `is_active` to `false`, if this is consistent with the project's administrative conventions.

Dedicated deactivation endpoints are optional. Do not implement duplicate endpoints solely to toggle a Boolean field unless a separate workflow or permission requires them.

Deactivation must prevent new selections while preserving historical order data.

## 6. Optional Reference Image Endpoints

Implement reference-image endpoints only if customer-uploaded images are part of the agreed Leeza Cakes workflow.

### 6.1 Upload reference image

The endpoint path and ownership model must be determined by the workflow that owns the draft or cart item.

For example, a cart-owned upload could use:

`POST /api/v1/cart/items/{cart_item_id}/reference-images/`

**Content type:** `multipart/form-data`

Validate file type, actual content, size, authorization, ownership, storage permissions, and retention policy.

Do not expose private reference images through publicly accessible URLs by default.

The customization app must not create an independent upload lifecycle if the cart or another workflow owns these files.

## 7. Request and Response Rules

### Selection request

The selection payload must identify options and choices using stable identifiers. The server must resolve names, eligibility, and prices from its database.

Do not accept authoritative fields such as:

- Product price.
- Choice price adjustment.
- Customization total.
- Final payable amount.
- Order status.

Customer-entered text is permitted only for options configured to accept text.

### Response stability

Public response schemas should change deliberately and be documented in OpenAPI.

Avoid returning complete Django model objects or arbitrary database fields. Use explicit serializers.

### Pagination

Administrative list endpoints must use shared pagination settings. Public option and choice endpoints may return a bounded collection when the product configuration is small and predictable.

## 8. Error Contract

Follow the project's existing `apps.common` error format. If none exists, establish one consistent format across the API.

Expected status codes:

| Status | Meaning |
|---|---|
| `200 OK` | Successful retrieval, update, or validation |
| `201 Created` | Resource created |
| `204 No Content` | Successful operation with no response body |
| `400 Bad Request` | Invalid selections, fields, or configuration |
| `401 Unauthorized` | Authentication required or invalid |
| `403 Forbidden` | Caller lacks required permissions |
| `404 Not Found` | Resource missing or not publicly accessible |
| `405 Method Not Allowed` | HTTP method unsupported |
| `415 Unsupported Media Type` | Unsupported request content type |
| `429 Too Many Requests` | Rate limit exceeded, if configured |
| `500 Internal Server Error` | Unexpected failure without sensitive diagnostic details |

Do not reveal internal database errors, filesystem paths, stack traces, environment variables, or storage credentials.

## 9. Authentication and Permissions Matrix

| Endpoint group | Anonymous user | Customer | Authorized staff |
|---|---|---|---|
| Public product options | Read eligible options | Read eligible options | Read |
| Public product choices | Read eligible choices | Read eligible choices | Read |
| Selection validation | Validate public selections | Validate public selections | Validate |
| Administrative option management | Denied | Denied | Allowed by permission |
| Administrative choice management | Denied | Denied | Allowed by permission |
| Product customization configuration | Denied | Denied | Allowed by permission |
| Private reference images | Denied by default | Authorized owner only | Restricted by explicit policy |

The exact staff permission names must follow the project's authentication and authorization design.

## 10. OpenAPI Requirements

Document every implemented endpoint in the existing OpenAPI schema.

Include:

- Request and response schemas.
- Required and optional fields.
- Supported input types.
- Authentication and permission requirements.
- Selection constraints.
- Pricing semantics.
- Pagination and filtering.
- Error responses.
- Upload content types, if implemented.
- Examples for valid and invalid selections.

Use the project's existing DRF Spectacular setup. Do not add a separate API documentation system.

## 11. Testing Requirements

Tests must cover:

1. Public option retrieval for a valid published product.
2. Options unavailable for unpublished or archived products.
3. Inactive options and choices are not exposed publicly.
4. Product-specific eligibility is enforced.
5. Choices cannot be submitted against the wrong option.
6. Required options are validated.
7. Single-choice and multiple-choice limits are enforced.
8. Duplicate selections are rejected where appropriate.
9. Text values respect validation constraints.
10. Prices are calculated from trusted database records.
11. Product and variant pricing are not double-counted.
12. Invalid or tampered price fields cannot influence server pricing.
13. Administrative endpoints enforce permissions.
14. Product-option and option-choice relationships are validated.
15. Deactivated options do not invalidate historical order snapshots.
16. Cart integration revalidates selections.
17. OpenAPI request and response schemas match implementation.
18. Private upload access and ownership are enforced, if uploads are implemented.

Use isolated test data. Do not modify production Supabase records.

## 12. Implementation Rules for AI Coding Agents

Before implementation:

1. Read `customization_structure.md`.
2. Inspect existing customization and catalogue models.
3. Confirm how catalogue variants represent cake sizes and prices.
4. Confirm the agreed customization pricing policy.
5. Inspect `apps.common` for error and pagination conventions.
6. Inspect authentication and staff permissions.
7. Inspect cart and order interfaces before designing integration.
8. Confirm whether reference-image uploads are required.

During implementation:

- Keep business validation reusable outside API views.
- Do not duplicate catalogue models or pricing.
- Do not trust frontend-supplied prices.
- Do not expose inactive or ineligible options.
- Do not create duplicate endpoints without a clear use case.
- Do not create empty modules or placeholder endpoints.
- Do not introduce additional dependencies without justification.
- Do not run migrations against Supabase, push changes, or deploy without explicit approval.

After implementation:

- Run Ruff and Django checks.
- Run relevant tests and the full test suite.
- Check migration consistency without applying migrations.
- Validate the generated OpenAPI schema.
- Review the final diff and report actual results.

## 13. Definition of Done

The customization API is complete when:

- Public endpoints return only eligible product-specific options and choices.
- Selection validation enforces the agreed business rules.
- Pricing adjustments are server-authoritative.
- Administrative endpoints require explicit permissions.
- Cart and order integration preserves data integrity.
- Historical order snapshots remain unchanged when options are edited.
- Tests, Ruff, and Django checks pass.
- OpenAPI documentation matches the implemented API.
- Optional features are implemented only when required.
- Any intentional deviation from this contract is documented in this file and `customization_structure.md`.

## 14. Decisions Required Before Implementation

Confirm these decisions against the actual business workflow:

1. Whether cake size is a catalogue variant or a customization option.
2. Whether customers can select multiple flavours or fillings.
3. Whether customization charges are per cake, per unit, or size-dependent.
4. Whether a separate validation endpoint is useful beyond cart validation.
5. Whether reference-image uploads are required and who owns their lifecycle.
6. Which staff roles can manage options and prices.
7. Whether options need availability windows or stock-related restrictions.

Do not invent answers for unresolved business requirements. Finalize them before implementing models, migrations, or pricing logic.