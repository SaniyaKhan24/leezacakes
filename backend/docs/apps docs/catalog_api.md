# Catalog API — Endpoint Specification

**Project:** Leeza Cakes  
**Application:** `apps.catalog`  
**Base path:** `/api/v1/catalog/`  
**Status:** API contract specification  
**Audience:** Backend developers, frontend developers, and AI coding agents

---

## 1. Purpose

This document defines the API contract for product categories, published products, product images, product variants, and administrative catalogue management.

The catalogue is the source of truth for product information and current catalogue pricing. The cart and orders applications must validate product eligibility and prices on the server.

All endpoints implemented in this application must follow this contract unless a documented architectural decision changes it.

## 2. API Conventions

### Base URL

Development example:

`http://localhost:8000/api/v1/catalog/`

### Response format

Use JSON for request and response bodies, except when a specifically documented upload endpoint requires multipart form data.

Use Django REST Framework's standard HTTP status codes and a consistent project-wide error format.

Do not introduce a catalogue-specific response envelope if the project already has an established response convention.

### Identifiers

- Use database IDs or another explicitly chosen stable identifier consistently.
- Use product slugs for public product-detail URLs.
- Use category slugs for public category-detail URLs.
- Do not expose internal database implementation details unnecessarily.

### Pagination

Product and category list endpoints must be paginated.

Use the pagination policy defined by `apps.common` or the project's global DRF settings. Do not create a conflicting pagination format.

### Monetary values

- Serialize monetary values as decimal strings to avoid floating-point precision loss.
- Include the currency code wherever price information is returned.
- Never trust a price supplied by the frontend.
- Do not calculate authoritative order totals in the frontend.

### Visibility

Public endpoints must not expose draft, archived, or otherwise ineligible products. Administrative endpoints may expose them to authorized staff.

---

## 3. Public Category Endpoints

### 3.1 List categories

`GET /api/v1/catalog/categories/`

**Purpose:** Return active categories suitable for public catalogue navigation.

**Authentication:** Not required.

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `page` | Integer | Page number, if supported by configured pagination |
| `page_size` | Integer | Requested page size, bounded by server configuration |
| `parent` | Category ID or supported identifier | Filter by parent category if hierarchy is enabled |

**Rules:**

- Return active categories only.
- Do not expose inactive categories to anonymous users.
- Use deterministic ordering, such as `sort_order` followed by name.
- If hierarchical categories are not implemented, omit the `parent` filter.

**Example response:**

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Birthday Cakes",
      "slug": "birthday-cakes",
      "description": "Cakes for birthday celebrations.",
      "image": null,
      "parent": null
    },
    {
      "id": 2,
      "name": "Chocolate Cakes",
      "slug": "chocolate-cakes",
      "description": "Chocolate cakes for every occasion.",
      "image": null,
      "parent": null
    }
  ]
}
```

The exact pagination envelope must match the project's configured DRF pagination class.

### 3.2 Retrieve category details

`GET /api/v1/catalog/categories/{slug}/`

**Purpose:** Retrieve an active category and its public metadata.

**Authentication:** Not required.

**Success:** `200 OK`

**Not found:** `404 Not Found`

The response must contain only public category fields. If products are included in the category response, they must follow the same publication and visibility rules as the product-list endpoint.

Do not embed an unbounded list of products in a category response. Prefer a separate product-list request filtered by category.

---

## 4. Public Product Endpoints

### 4.1 List products

`GET /api/v1/catalog/products/`

**Purpose:** Return published products that are eligible for public display.

**Authentication:** Not required.

**Supported query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `page` | Integer | Page number |
| `page_size` | Integer | Requested page size, subject to server limits |
| `category` | Category slug or documented category identifier | Filter by category |
| `search` | String | Basic product-name or description search, if enabled |
| `min_price` | Decimal | Minimum eligible price |
| `max_price` | Decimal | Maximum eligible price |
| `featured` | Boolean | Filter featured products |
| `ordering` | String | One of the explicitly supported ordering fields |

Only implement filters supported by the actual model and business requirements.

Allowed ordering values should be documented explicitly, for example:

- `name`
- `-name`
- `created_at`
- `-created_at`
- `price`
- `-price`

Price ordering and filtering must have a defined meaning for products with variants. If the effective price is the lowest active variant price, implement that rule consistently. Do not expose arbitrary ORM fields through `ordering`.

**Example request:**

`GET /api/v1/catalog/products/?category=chocolate-cakes&featured=true&page=1`

**Example response:**

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 101,
      "name": "Chocolate Truffle Cake",
      "slug": "chocolate-truffle-cake",
      "short_description": "Rich chocolate truffle cake.",
      "category": {
        "id": 2,
        "name": "Chocolate Cakes",
        "slug": "chocolate-cakes"
      },
      "base_price": "650.00",
      "currency": "INR",
      "primary_image": {
        "url": "https://example.com/media/catalog/chocolate-truffle.jpg",
        "alt_text": "Chocolate truffle cake"
      },
      "is_featured": true,
      "variants": []
    }
  ]
}
```

The image URL is illustrative. Actual URLs must come from the configured storage backend.

The `base_price` and `variants` representation must reflect the final pricing model. Do not return contradictory product-level and variant-level prices.

### 4.2 Retrieve product details

`GET /api/v1/catalog/products/{slug}/`

**Purpose:** Return the complete public representation of a published product.

**Authentication:** Not required.

**Success:** `200 OK`

**Not found:** `404 Not Found` for missing, unpublished, archived, or otherwise non-public products.

**Response fields:**

- Product ID.
- Name and slug.
- Short and full descriptions.
- Public category metadata.
- Applicable base price and currency.
- Ordered product images.
- Active variants and their prices, when variants exist.
- Featured status.
- Public preparation-time or weight information, if configured.
- Public availability information, if the availability policy has been implemented.

Never expose internal notes, unpublished records, administrative-only fields, or unrestricted model data.

### 4.3 Featured products

`GET /api/v1/catalog/products/featured/`

**Purpose:** Return a paginated or explicitly bounded list of featured published products.

**Authentication:** Not required.

**Rules:**

- Return published products only.
- Apply the same visibility and availability policy as the regular listing.
- Use deterministic ordering.
- Limit the number of returned products or use standard pagination.

This endpoint is optional. If the normal product-list endpoint already supports `featured=true` and that is sufficient for the frontend, do not implement a duplicate endpoint.

---

## 5. Product Variant Endpoints

### 5.1 Retrieve product variants

`GET /api/v1/catalog/products/{slug}/variants/`

**Purpose:** Return active variants belonging to a published product.

**Authentication:** Not required.

**Success:** `200 OK`

**Not found:** `404 Not Found` if the product is not publicly accessible.

**Rules:**

- Return variants for the requested product only.
- Return active variants only.
- Include the variant ID, display name, price, currency, and any supported public attributes.
- Do not expose internal inventory or administrative fields.
- If variants are embedded in the product-detail response, this endpoint is optional and should not duplicate unnecessary functionality.

**Example response:**

```json
{
  "results": [
    {
      "id": 501,
      "name": "500 g",
      "price": "650.00",
      "currency": "INR"
    },
    {
      "id": 502,
      "name": "1 kg",
      "price": "1100.00",
      "currency": "INR"
    }
  ]
}
```

The example prices are illustrative only.

### 5.2 Variant validation for cart operations

The catalogue does not need a public endpoint that accepts a product ID and returns a trusted checkout price merely because the frontend requests one.

The cart service must validate the selected product and variant using server-side catalogue queries or a documented internal service interface.

If an internal validation endpoint is genuinely required, it must be authenticated appropriately, restricted to trusted service usage, and excluded from public access.

---

## 6. Administrative Category Endpoints

All administrative endpoints require authenticated users with explicit catalogue-management permissions. Being logged in is not sufficient.

### 6.1 Create category

`POST /api/v1/catalog/admin/categories/`

**Permission:** Authorized catalogue staff.

**Request fields:**

- `name` — required.
- `slug` — required or generated according to the documented slug policy.
- `description` — optional.
- `image` — optional.
- `parent` — optional if hierarchical categories are enabled.
- `is_active` — permitted only for authorized staff.
- `sort_order` — optional.

**Success:** `201 Created`

**Validation:** Reject duplicate slugs, invalid parent relationships, and unsupported fields.

### 6.2 Update category

`PATCH /api/v1/catalog/admin/categories/{id}/`

**Permission:** Authorized catalogue staff.

Support partial updates of permitted category fields.

**Success:** `200 OK`

**Validation:** Enforce uniqueness and category hierarchy rules.

### 6.3 Deactivate category

`POST /api/v1/catalog/admin/categories/{id}/deactivate/`

**Permission:** Authorized catalogue staff.

**Success:** `200 OK` or `204 No Content`, consistently with the project's API conventions.

Deactivation must not cascade-delete products or historical order data.

This endpoint is optional if the administrative update endpoint safely supports changing `is_active`.

---

## 7. Administrative Product Endpoints

### 7.1 List products for administration

`GET /api/v1/catalog/admin/products/`

**Permission:** Authorized catalogue staff.

**Purpose:** List products across supported statuses, including drafts and archived products.

**Optional filters:**

- `status`
- `category`
- `search`
- `page`
- `page_size`

Apply pagination and explicit filtering rules.

### 7.2 Create product

`POST /api/v1/catalog/admin/products/`

**Permission:** Authorized catalogue staff.

**Request fields may include:**

- `name`
- `slug`
- `description`
- `short_description`
- `category`
- `status`
- `is_featured`
- `base_price`, if the selected pricing model uses it
- `currency`
- `weight_description`
- `preparation_time`

Do not accept arbitrary fields or client-generated prices for unrelated entities.

**Success:** `201 Created`

**Rules:**

- Validate the category.
- Validate prices and currency.
- Enforce slug uniqueness.
- Enforce the product/variant pricing model.
- Do not automatically publish a product unless the request and permission policy explicitly allow it.

### 7.3 Retrieve product for administration

`GET /api/v1/catalog/admin/products/{id}/`

**Permission:** Authorized catalogue staff.

Return the administrative representation, including status and permitted internal management fields.

Do not expose secrets or unrelated customer information.

### 7.4 Update product

`PATCH /api/v1/catalog/admin/products/{id}/`

**Permission:** Authorized catalogue staff.

**Success:** `200 OK`

The endpoint must:

- Validate partial updates.
- Prevent unauthorized changes to restricted fields.
- Preserve data integrity.
- Apply pricing and publication rules.
- Avoid modifying historical order snapshots.

### 7.5 Publish product

`POST /api/v1/catalog/admin/products/{id}/publish/`

**Permission:** Authorized catalogue staff with publication privileges.

**Success:** `200 OK`

Before publication, validate the minimum required product data, category eligibility, pricing configuration, and any required image or variant rules.

A product must not become publicly visible if required fields or pricing are invalid.

### 7.6 Archive product

`POST /api/v1/catalog/admin/products/{id}/archive/`

**Permission:** Authorized catalogue staff.

**Success:** `200 OK` or `204 No Content`, according to the project's response conventions.

Archiving must prevent new purchases while preserving references required by historical orders.

### 7.7 Featured status

Featured status may be managed through the product update endpoint if permissions and validation are adequate.

Do not create a separate endpoint solely to toggle a Boolean field unless a distinct permission or workflow justifies it.

---

## 8. Administrative Product Image Endpoints

Image management may be implemented through nested product endpoints or validated nested writes. Select one approach and document it consistently.

If dedicated endpoints are needed, use the following contract.

### 8.1 Add product image

`POST /api/v1/catalog/admin/products/{id}/images/`

**Permission:** Authorized catalogue staff.

**Content type:** `multipart/form-data` when uploading a file.

**Fields:**

- `image` — required.
- `alt_text` — optional or required according to accessibility policy.
- `sort_order` — optional.
- `is_primary` — optional.

**Success:** `201 Created`

Validate the actual image, permitted format, file size, and product relationship.

### 8.2 Update product image metadata

`PATCH /api/v1/catalog/admin/products/{id}/images/{image_id}/`

**Permission:** Authorized catalogue staff.

Allow only supported metadata changes, such as alt text, ordering, and primary status.

Validate that the image belongs to the specified product.

### 8.3 Delete product image

`DELETE /api/v1/catalog/admin/products/{id}/images/{image_id}/`

**Permission:** Authorized catalogue staff.

**Success:** `204 No Content`

Safely coordinate database changes and storage cleanup. Do not leave the product in an invalid state if a primary image is required.

These endpoints are optional if the project adopts a tested nested-image management strategy.

---

## 9. Administrative Variant Endpoints

Implement variant endpoints only if the chosen data model supports variants.

### 9.1 Create variant

`POST /api/v1/catalog/admin/products/{id}/variants/`

**Permission:** Authorized catalogue staff.

**Request fields:**

- `name`
- `sku`, if supported
- `price`
- `currency`
- `is_active`
- `sort_order`
- Supported variant attributes.

**Success:** `201 Created`

Validate price, SKU uniqueness, currency, and product ownership.

### 9.2 Update variant

`PATCH /api/v1/catalog/admin/products/{id}/variants/{variant_id}/`

**Permission:** Authorized catalogue staff.

Validate that the variant belongs to the specified product.

### 9.3 Deactivate variant

`POST /api/v1/catalog/admin/products/{id}/variants/{variant_id}/deactivate/`

**Permission:** Authorized catalogue staff.

Deactivation must prevent new purchases but preserve historical order references.

As with products, a normal update endpoint may be sufficient if the same invariants and permissions are enforced.

---

## 10. Error Response Contract

Follow the existing project-wide error format. If none has been established, use a consistent format such as:

```json
{
  "error": {
    "code": "validation_error",
    "message": "The request contains invalid data.",
    "details": {
      "slug": ["A category with this slug already exists."]
    }
  }
}
```

The exact envelope must be consistent with `apps.common` and the project's DRF exception handler. Do not implement a competing format in `apps.catalog`.

Expected status codes:

| Status | Meaning |
|---|---|
| `200 OK` | Successful retrieval or update |
| `201 Created` | Resource created |
| `204 No Content` | Successful deletion or operation with no response body |
| `400 Bad Request` | Invalid input or unsupported filter value |
| `401 Unauthorized` | Authentication required or invalid |
| `403 Forbidden` | Authenticated caller lacks permission |
| `404 Not Found` | Resource does not exist or is not publicly visible |
| `405 Method Not Allowed` | Unsupported HTTP method |
| `415 Unsupported Media Type` | Unsupported upload or request content type |
| `429 Too Many Requests` | Rate limit exceeded, if configured |
| `500 Internal Server Error` | Unexpected server failure without sensitive diagnostic details |

Do not return stack traces, SQL details, environment variables, storage credentials, or internal exception messages.

---

## 11. Authentication and Permissions Matrix

| Endpoint group | Anonymous user | Authenticated customer | Authorized catalogue staff |
|---|---|---|---|
| Public categories | Read | Read | Read |
| Public products | Read | Read | Read |
| Public variants | Read | Read | Read |
| Administrative categories | Denied | Denied | Allowed by permission |
| Administrative products | Denied | Denied | Allowed by permission |
| Administrative images | Denied | Denied | Allowed by permission |
| Administrative variants | Denied | Denied | Allowed by permission |

Administrative permissions must be enforced on the server for every request. Frontend route protection is not a security boundary.

---

## 12. OpenAPI Documentation

All implemented catalogue endpoints must appear in the project's OpenAPI schema.

Requirements:

- Accurate request and response schemas.
- Explicit authentication and permission requirements.
- Documented pagination and filtering.
- Examples for product and category representations.
- Documented validation errors.
- Correct content types for image uploads.
- Clear separation between public and administrative endpoints.
- No undocumented endpoint behavior.

Use the project's existing DRF Spectacular configuration and documentation routes. Do not create a second OpenAPI generator.

---

## 13. API Testing Requirements

Tests must cover:

1. Public category listing and detail.
2. Public product listing and detail.
3. Draft and archived products are hidden publicly.
4. Inactive categories and variants are handled correctly.
5. Filtering, sorting, and pagination.
6. Invalid filter and ordering parameters.
7. Price serialization and validation.
8. Product and variant relationship validation.
9. Administrative permissions for all write operations.
10. Unauthorized fields cannot be modified.
11. Image upload validation and image ownership.
12. Publication and archive transitions.
13. Stable historical order snapshots after catalogue changes.
14. API response schemas and status codes.
15. Query efficiency for product lists and related images/variants.

Tests must use isolated test data and must not modify production Supabase records.

---

## 14. Implementation Rules for AI Coding Agents

Before implementing:

1. Read `catalog_structure.md`.
2. Inspect existing `apps.catalog`, `apps.common`, `apps.accounts`, `apps.cart`, and `apps.orders` code.
3. Inspect the current URL configuration, authentication strategy, pagination settings, exception format, and OpenAPI configuration.
4. Confirm whether migrations or models already exist.
5. Resolve the variant and pricing decisions before writing models.
6. Match existing project conventions rather than creating duplicate infrastructure.

During implementation:

- Do not create endpoints that duplicate existing functionality without a reason.
- Do not expose draft or archived products publicly.
- Do not trust client-supplied prices.
- Do not use floats for monetary calculations.
- Do not let catalogue changes rewrite historical orders.
- Do not create empty modules or placeholder endpoints.
- Do not introduce additional dependencies without justification.
- Do not run migrations against Supabase, push changes, or deploy without explicit approval.

After implementation:

- Run Ruff and Django checks.
- Run the relevant tests and the full test suite.
- Check migration consistency without applying migrations.
- Validate the generated OpenAPI schema.
- Review the final diff.
- Report implemented endpoints, checks performed, failures, and remaining work accurately.

**Completion criterion:** The implemented API must match this contract, the model specification in `catalog_structure.md`, and the project's shared conventions. Any intentional deviation must be documented in both catalogue documents.