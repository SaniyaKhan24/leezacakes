# Catalog App — Architecture and Structure

**Project:** Leeza Cakes  
**Django application:** `apps.catalog`  
**Document type:** Architecture specification  
**Status:** Architecture defined; implementation pending  
**Audience:** AI coding agents, backend developers, reviewers, and maintainers

---

## 1. Purpose and Scope

The `catalog` application is the source of truth for products that Leeza Cakes offers for sale.

It defines what products exist, how they are organized, what customers can see, which options are available for purchase, and the catalogue information used by cart, customization, orders, and search.

The catalogue must support standard cakes, potentially preconfigured products, and products that permit customer-specific customization.

### Responsibilities

The catalogue app owns:

- Product creation and management.
- Product categories.
- Product descriptions and display information.
- Product slugs and public identifiers.
- Product images and image ordering.
- Product publication and visibility.
- Sellable product variants where applicable.
- Base prices and variant price differences.
- Product availability and sale eligibility.
- Catalogue-specific attributes and labels.
- Product search/filter metadata.
- Administrative catalogue management.
- Product-level validation and business rules.
- Public product and category read APIs.

### Explicitly outside its scope

- Customer identity and authentication — `apps.accounts`.
- Custom cake design requests and inscriptions — `apps.customization`.
- Shopping cart lifecycle and quantities — `apps.cart`.
- Order creation, order status, and historical purchase snapshots — `apps.orders`.
- Payment processing and refunds — `apps.payments`.
- Notification delivery — `apps.notifications`.
- Search query execution and search optimization — `apps.search`.
- Shared API conventions and health endpoints — `apps.common`.

The catalogue may expose product data to other apps through stable model relationships and service interfaces. It must not duplicate their business logic.

---

## 2. Architectural Principles

1. **Single source of truth:** Product identity and catalogue data belong to this application.
2. **Explicit sale eligibility:** Publication, availability, and purchasability must be clearly distinguished.
3. **Server-authoritative pricing:** The client must never determine the authoritative product price.
4. **Historical stability:** Existing orders must retain the product description and price that applied at purchase time.
5. **Consistent identifiers:** Use stable primary keys and deliberate public slugs.
6. **Database integrity:** Enforce uniqueness and other data invariants at the database level where appropriate.
7. **No duplicate catalogue data:** Search and cart must reference catalogue records rather than maintain competing product definitions.
8. **Controlled administration:** Product publication and pricing changes require appropriate staff permissions.
9. **Validated media:** Product images must be validated and stored using an appropriate storage backend.
10. **Incremental implementation:** Build the minimum useful catalogue model before introducing inventory systems, complex pricing engines, or external search infrastructure.

---

## 3. Recommended Directory Structure

Implement this structure under `backend/apps/catalog/` as needed.

```text
catalog/
├── __init__.py
├── apps.py
├── models.py
├── admin.py
├── serializers.py
├── views.py
├── urls.py
├── services.py
├── selectors.py
├── permissions.py
├── filters.py
├── pagination.py
├── validators.py
├── constants.py
├── exceptions.py
├── signals.py
├── tasks.py
├── migrations/
│   └── __init__.py
└── tests/
    ├── __init__.py
    ├── factories.py
    ├── test_categories.py
    ├── test_products.py
    ├── test_variants.py
    ├── test_pricing.py
    ├── test_availability.py
    ├── test_serializers.py
    ├── test_permissions.py
    ├── test_services.py
    ├── test_selectors.py
    ├── test_admin.py
    └── test_api.py
```

Create modules only when their responsibilities are needed. Do not create empty files just to match the proposed structure.

### Module responsibilities

| Module | Responsibility |
|---|---|
| `apps.py` | Django application configuration |
| `models.py` | Category, product, product image, and variant models |
| `admin.py` | Staff-facing catalogue management |
| `serializers.py` | Request validation and public/admin representations |
| `views.py` | HTTP request handling |
| `urls.py` | Catalogue endpoint routing |
| `services.py` | Product publication, price changes, and other multi-step operations |
| `selectors.py` | Read-only product and category queries |
| `permissions.py` | Staff and catalogue-management authorization |
| `filters.py` | Category, price, availability, and other supported filtering |
| `pagination.py` | Catalogue list pagination if a dedicated policy is necessary |
| `validators.py` | Product-specific and variant-specific validation |
| `constants.py` | Stable catalogue-specific constants |
| `exceptions.py` | Catalogue-domain errors |
| `signals.py` | Minimal integrations, only where justified |
| `tasks.py` | Background image processing or indexing, if infrastructure exists |
| `tests/` | Model, service, permission, API, and regression tests |

---

## 4. Data Model Overview

The initial catalogue should use these core concepts:

1. `Category` — groups products.
2. `Product` — defines the product's identity and public-facing information.
3. `ProductImage` — stores product imagery and display order.
4. `ProductVariant` — represents a distinct sellable option when products have meaningful variants.

The implementation must decide whether every product needs a variant. If a product can be sold directly at one price, avoid forcing customers or downstream applications to select an artificial variant.

If the project adopts a universal variant model for consistent checkout and stock management, document that decision and ensure simple products remain easy to create and purchase.

### Relationships

```text
Category
   |
   | one-to-many
   v
Product
   |
   +---- one-to-many ----> ProductImage
   |
   +---- one-to-many ----> ProductVariant
                              |
                              v
                         Cart Item
                              |
                              v
                          Order Item
```

The diagram describes logical relationships. Cart and order models belong to their respective applications and should reference catalogue records through appropriate foreign keys or stable identifiers.

A product may have no variants when sold directly, unless the final schema explicitly requires all products to have at least one variant.

---

## 5. Category Model

### Purpose

`Category` groups products into navigable customer-facing collections.

Possible categories include:

- Birthday Cakes
- Chocolate Cakes
- Wedding Cakes
- Photo Cakes
- Designer Cakes
- Cupcakes
- Seasonal Collections

These are examples, not mandatory seed data.

### Recommended fields

| Field | Purpose |
|---|---|
| `id` | Primary key |
| `name` | Customer-facing category name |
| `slug` | Stable URL-friendly identifier |
| `description` | Optional category description |
| `image` | Optional category image |
| `parent` | Optional self-referential parent category |
| `is_active` | Whether the category is available for public navigation |
| `sort_order` | Explicit display ordering |
| `created_at` | Creation timestamp |
| `updated_at` | Last-update timestamp |

Use a parent category only if nested categories are required. Do not implement a complex tree library without a real requirement.

### Category invariants

- Slugs must be unique according to the selected URL strategy.
- A category cannot be its own parent.
- Cyclic parent relationships must be prevented if hierarchical categories are enabled.
- Inactive categories must not appear in public navigation.
- Public category listings must not expose unpublished products.
- Deactivation should not delete historical order data.

Category deletion policy must account for products that reference the category. Prefer controlled deactivation or reassignment over cascading deletion of catalogue records.

---

## 6. Product Model

### Purpose

`Product` represents the conceptual cake or other sellable catalogue item.

It owns public product information, publication state, category association, and catalogue-level attributes.

### Recommended fields

| Field | Purpose |
|---|---|
| `id` | Stable primary key |
| `name` | Product name |
| `slug` | Public URL identifier |
| `description` | Detailed product description |
| `short_description` | Optional summary |
| `category` | Foreign key to `Category` |
| `status` | Draft, published, or archived |
| `is_featured` | Whether the product is promoted |
| `base_price` | Authoritative product price when no separate variant price applies |
| `currency` | Currency code, using a consistent project policy |
| `weight_description` | Optional customer-facing weight information |
| `preparation_time` | Preparation lead time, if applicable |
| `created_at` | Creation timestamp |
| `updated_at` | Last-update timestamp |
| `published_at` | Publication timestamp, when applicable |

These are proposed fields, not a mandate to store redundant data. If variants own all prices, avoid a competing `base_price` that can contradict them.

### Product status

Use an explicit status policy:

- `DRAFT`: not publicly visible or purchasable.
- `PUBLISHED`: eligible for public display, subject to availability and category rules.
- `ARCHIVED`: retained for administrative or historical purposes but not offered as a new purchase.

A published product is not necessarily available to purchase at every moment.

### Product invariants

- Product names and descriptions must be validated.
- Public slugs must be unique according to the chosen URL strategy.
- Prices must be non-negative and use decimal arithmetic, never binary floating-point arithmetic.
- Currency must follow the project's supported-currency policy.
- Draft and archived products must not be purchasable through public cart endpoints.
- Unpublishing a product must not rewrite historical orders.
- Price changes must not silently alter existing order totals.
- Featured status must not override publication or availability rules.
- Category visibility and product visibility must be evaluated consistently.

### Product slugs

Slugs should be stable and unique. Do not automatically change a published slug whenever a product name changes unless the project explicitly adopts that policy.

If slug changes are permitted, consider redirects or an alternative stable public identifier to prevent broken links.

---

## 7. Product Image Model

### Purpose

`ProductImage` manages multiple images for a product.

A cake may need a primary image, gallery images, and optional detail views.

### Recommended fields

| Field | Purpose |
|---|---|
| `id` | Primary key |
| `product` | Foreign key to `Product` |
| `image` | Image storage reference |
| `alt_text` | Accessible image description |
| `sort_order` | Gallery ordering |
| `is_primary` | Whether this is the primary product image |
| `created_at` | Creation timestamp |

### Image invariants

- Images must belong to a product.
- Image uploads must be validated for actual image content and allowed file formats.
- Enforce file-size limits.
- Generate safe storage names rather than trusting user-supplied filenames.
- Do not serve untrusted uploaded files as executable content.
- Ensure each product has at most one primary image where required.
- If a primary image is deleted, define how the primary image is reassigned.
- Product image storage must be configurable for local development and production object storage.
- Database deletion and physical storage cleanup must be handled safely.

Do not store image binaries directly in PostgreSQL unless there is a specific, justified requirement. Store a reference to the media object.

If asynchronous image processing is added, use the configured task infrastructure and make failures observable.

---

## 8. Product Variant Model

### Purpose

`ProductVariant` represents a distinct sellable configuration of a product.

Examples may include different weights, sizes, or standard options that have independent prices or availability.

For example, a chocolate cake might have 500 g, 1 kg, and 2 kg variants.

### Recommended fields

| Field | Purpose |
|---|---|
| `id` | Primary key |
| `product` | Foreign key to `Product` |
| `name` | Customer-facing variant label |
| `sku` | Optional unique stock-keeping identifier |
| `price` | Authoritative price for this variant |
| `currency` | Currency under the project's currency policy |
| `is_active` | Whether the variant can be selected |
| `sort_order` | Display ordering |
| `created_at` | Creation timestamp |
| `updated_at` | Last-update timestamp |

Add stock or inventory fields only after deciding how inventory will be managed. A simple `stock_quantity` field is not sufficient for every inventory or preorder workflow.

### Variant invariants

- A variant must belong to a valid product.
- Inactive variants must not be purchasable.
- A variant belonging to an unpublished or archived product must not be purchasable.
- Prices must be non-negative and use decimal arithmetic.
- SKU uniqueness must be enforced if SKUs are used.
- The API must return only active variants of publicly visible products.
- Cart and order operations must validate variant ownership and eligibility.
- Variant deactivation must not delete historical order items.

If variants are optional, define one consistent pricing strategy for products with and without variants. Never allow the product-level price and variant-level price to contradict each other.

---

## 9. Pricing Architecture

### Authoritative price

The catalogue is the source of truth for current product and variant prices.

Clients may submit product IDs, variant IDs, quantities, and supported customization selections. They must not be trusted to supply authoritative prices or totals.

The cart and orders applications must retrieve or validate prices server-side.

### Money representation

- Use Django `DecimalField` for monetary database fields.
- Use Python `Decimal` for arithmetic.
- Never use binary floating-point arithmetic for prices.
- Define currency precision and rounding rules.
- Define how currency is represented and whether multiple currencies are supported.
- Avoid implicit currency conversion.

### Price changes

A catalogue price change affects future price calculations according to the project's pricing policy.

It must not silently rewrite historical orders. The orders application must preserve the price, currency, product description, variant description, and other relevant purchase-time information in its order-item snapshot.

If the cart is intended to retain the price initially displayed, the checkout flow must explicitly revalidate it and communicate price changes to the customer before purchase.

### Customization pricing

The catalogue may define base prices for products. The customization application owns the pricing rules for optional customization features when those rules are introduced.

The cart and orders applications must calculate the final amount using validated catalogue prices and validated customization charges. No client-supplied total is authoritative.

---

## 10. Availability and Inventory Boundaries

Publication, availability, and inventory are distinct concepts.

- **Publication:** Is the product visible in the public catalogue?
- **Availability:** Can it currently be offered for purchase?
- **Inventory:** Is there stock or production capacity available?
- **Preparation lead time:** How long is required to prepare the product?
- **Orderability:** Is the product eligible for the customer's intended order?

For made-to-order cakes, a stock counter may not accurately represent real availability. Availability may depend on preparation lead time, production capacity, delivery date, or manual approval.

Do not implement a full inventory system until the business rules are defined.

If inventory is required, document ownership, reservations, concurrency, overselling prevention, and release behavior before implementation.

The catalogue may expose current availability information, but the checkout process must revalidate it. A product shown as available in an earlier catalogue response may become unavailable before checkout.

---

## 11. Application Layering

The request path should follow this structure:

```text id="4drmsp"
HTTP Request
    |
    v
config.urls
    |
    v
apps.catalog.urls
    |
    v
Authentication / Permissions
    |
    v
Views
    |
    v
Serializers
    |
    v
Catalogue Services
    |
    +----> Selectors / ORM Queries
    |
    +----> Category / Product / Image / Variant Models
    |
    v
Validated API Response
```

### Views

Views handle HTTP requests, apply permissions, validate input through serializers, invoke business operations, and return the correct status codes.

Views must not become the primary location for complex pricing, publication, or availability rules.

### Serializers

Serializers validate incoming data and produce explicit public representations.

Separate public read serializers from administrative write serializers where the allowed fields differ substantially.

Public serializers must never expose internal administration flags or arbitrary model fields.

### Services

Services own multi-step operations, such as:

- Creating or updating catalogue records with related data.
- Publishing and archiving products.
- Applying product or variant price changes.
- Enforcing primary-image changes.
- Applying product-specific availability rules.

Not every CRUD operation requires a service. Use one where it centralizes business invariants or coordinates multiple changes.

### Selectors

Selectors contain reusable read-only queries, such as:

- Listing published products.
- Retrieving a public product by slug.
- Listing active categories.
- Fetching active variants for a published product.
- Applying common filtering and ordering.

Selectors must not accidentally expose draft, archived, or inactive records to public callers.

### Permissions

Public users may read eligible published catalogue data.

Catalogue modifications require authorized staff permissions.

Public customers must not create, publish, edit, archive, or change prices on catalogue products through customer endpoints.

Django admin permissions and API permissions must both enforce the intended authorization policy.

---

## 12. Integration With Other Apps

### Accounts

Catalogue browsing should not require an account unless a specific feature requires authentication. Administrative changes require staff permissions.

### Customization

The customization application defines customer-selected personalization, inscriptions, design references, and customization pricing rules.

It may reference catalogue products or variants. The catalogue must not absorb customer-specific customization requests into product records.

### Cart

Cart items reference the selected product and, when applicable, the selected variant.

Before accepting or updating a cart item, the cart service must validate that:

- The product exists.
- The product is published.
- The variant belongs to that product, if supplied.
- The variant is active.
- The product is eligible for purchase.
- The submitted quantity and customization are valid.

The cart must not maintain a competing product or price database.

### Orders

Orders must store purchase-time snapshots rather than relying solely on mutable catalogue data.

An order item should preserve the relevant product name, variant description, selected options, unit price, currency, quantity, and final line amount.

Archiving or updating a product must not rewrite historical order snapshots.

### Payments

The payments application must use order totals calculated by trusted backend services. Catalogue prices must never be used as proof of successful payment.

### Search

The search application queries catalogue data. It may introduce a dedicated index later, but the catalogue remains the source of truth.

Search results must respect publication, category visibility, active variants, and availability rules.

### Notifications

The catalogue may provide product information to notification workflows when needed, but it must not implement email delivery or notification retries.

---

## 13. Public Catalogue Query Rules

Public catalogue selectors and APIs must consistently apply visibility rules.

At minimum:

- Exclude draft products.
- Exclude archived products.
- Exclude inactive categories where category visibility is required.
- Exclude inactive variants.
- Return only safe public fields.
- Apply deterministic ordering.
- Support pagination.
- Validate filters and sorting fields against an explicit allowlist.
- Avoid unbounded related-object queries.
- Use `select_related()` and `prefetch_related()` where appropriate to prevent avoidable N+1 queries.

Administrative endpoints may access draft and archived products when the caller has the necessary permissions.

Do not use a single unrestricted queryset for both public and administrative use without clearly separating their authorization rules.

---

## 14. Filtering and Sorting

The public catalogue may support:

- Category filtering.
- Product name search through the dedicated search app or a clearly defined basic filter.
- Minimum and maximum price.
- Featured products.
- Available products.
- Supported variant attributes.
- Explicit sort order, such as newest, name, or price where appropriate.

Only allow documented filter and ordering fields.

Validate minimum and maximum price values and reject invalid ranges.

Price filtering must have a clear meaning for products with variants. For example, it may filter by the lowest eligible variant price, but the implementation must document that behavior.

Do not expose arbitrary ORM field names through client-controlled ordering or filtering.

Advanced full-text search belongs in `apps.search`.

---

## 15. Django Admin

Configure administrative catalogue management for categories, products, images, and variants.

Requirements:

- Appropriate list displays, filters, and search fields.
- Readable category and product relationships.
- Clear publication and availability indicators.
- Explicit permissions for price changes and publication where necessary.
- Validation for related objects and price fields.
- No public ability to modify catalogue data.
- Protection against inconsistent primary-image and variant states.

If inline product images or variants are supported, ensure inline administration cannot bypass the relevant validation rules.

---

## 16. Media and Image Storage

Product images must be managed through Django's configured storage abstraction.

Development may use local media storage. Production should use a supported durable storage service when required by the deployment architecture.

Requirements:

- Never rely on the application's local filesystem for durable production media unless persistent storage is explicitly configured.
- Validate file content and size.
- Generate safe storage names.
- Avoid trusting original filenames or content types.
- Ensure media URLs are generated by the configured storage backend.
- Define cleanup behavior for replaced or deleted images.
- Do not delete a storage object before a related database operation is safely committed.
- Consider background cleanup or reconciliation for orphaned files.

Do not implement a public image-upload endpoint unless the catalogue administration workflow actually requires one.

---

## 17. Security Requirements

- Enforce staff permissions for catalogue modifications.
- Use explicit serializer fields.
- Reject unauthorized model fields and mass assignment.
- Validate price and currency inputs.
- Do not trust client-supplied prices or availability.
- Prevent unauthorized image uploads and file abuse.
- Avoid exposing unpublished products through public APIs.
- Do not reveal internal exception messages.
- Apply pagination and reasonable query limits.
- Use database constraints for uniqueness and critical invariants.
- Ensure product identifiers cannot be used to bypass authorization in administrative operations.
- Avoid public endpoints that enumerate internal records.
- Log meaningful administrative price and publication changes without logging unnecessary personal data.

---

## 18. Testing Strategy

### Category tests

Verify category creation, slug uniqueness, active status, hierarchy rules if enabled, and public visibility.

### Product tests

Verify:

- Product creation and validation.
- Slug uniqueness.
- Publication transitions.
- Draft and archived visibility.
- Price and currency validation.
- Category relationships.
- Public versus administrative query behavior.

### Image tests

Verify image ownership, file validation, ordering, primary-image invariants, and safe deletion behavior.

### Variant tests

Verify:

- Variant-to-product relationships.
- Variant pricing.
- Active/inactive status.
- Product publication restrictions.
- SKU uniqueness if applicable.
- Correct handling of products with and without variants.

### API tests

Verify:

- Public catalogue endpoints return only eligible products.
- Administrative endpoints require proper permissions.
- Unauthorized fields cannot be modified.
- Filtering, sorting, and pagination work as documented.
- Related data is serialized safely.
- Invalid price and variant selections are rejected.
- API responses match the OpenAPI schema.

### Integration tests

Verify:

- Cart can validate product and variant eligibility.
- Orders can create immutable price and product snapshots.
- Search respects catalogue publication and visibility.
- Catalogue changes do not mutate historical orders.

Tests must use isolated test data and must not depend on or mutate production Supabase data.

---

## 19. Implementation Order

Implement the catalogue in this sequence:

1. Inspect the existing app scaffold, project settings, dependency versions, and migration history.
2. Finalize product and category requirements.
3. Decide whether variants are mandatory or optional.
4. Decide the product and variant pricing model.
5. Decide the currency policy.
6. Decide whether inventory and preparation capacity are in scope.
7. Implement category and product models with validation and constraints.
8. Implement product images and storage integration.
9. Implement variants if required by the agreed design.
10. Implement public catalogue selectors and serializers.
11. Implement public read endpoints and administrative write endpoints.
12. Implement publication, pricing, and availability rules.
13. Add admin configuration and tests.
14. Define stable integration points for customization, cart, orders, and search.
15. Document all implemented endpoints in `catalog_api.md`.
16. Run Ruff, Django checks, production configuration checks, migration consistency checks, and the test suite.
17. Review the final diff and report actual verification results.

Do not run migrations against Supabase without explicit approval.

---

## 20. Definition of Done

The catalogue app is complete when:

- [ ] Category and product responsibilities are clearly separated.
- [ ] The pricing strategy is unambiguous.
- [ ] Variant behavior is documented and implemented consistently.
- [ ] Product publication and availability are distinct.
- [ ] Public queries exclude unpublished or ineligible products.
- [ ] Administrative write operations enforce staff permissions.
- [ ] Images use validated uploads and configured storage.
- [ ] Cart and orders can reference catalogue records without duplicating source-of-truth data.
- [ ] Historical orders remain stable after catalogue changes.
- [ ] Search consumes catalogue data rather than owning duplicate product records.
- [ ] API filters, ordering, and pagination are documented.
- [ ] Automated tests cover models, permissions, pricing, and endpoints.
- [ ] OpenAPI documents the implemented endpoints.
- [ ] Ruff checks pass.
- [ ] Django checks pass.
- [ ] Migration consistency checks pass.
- [ ] The full test suite passes.
- [ ] No secrets or unrelated changes are introduced.
- [ ] No database migrations, pushes, or deployments occurred without approval.

---

## 21. Instructions for AI Coding Agents

When implementing this specification:

1. Read this document before editing `apps.catalog`.
2. Inspect the actual repository and existing settings.
3. Do not invent complex inventory or pricing behavior without a documented requirement.
4. Do not trust client-supplied prices, product eligibility, or administrative fields.
5. Keep product data authoritative in the catalogue.
6. Preserve purchase-time snapshots in the orders application.
7. Do not duplicate product records in cart or search.
8. Implement meaningful code and tests rather than empty scaffolding.
9. Update `catalog_api.md` when endpoint behavior changes.
10. Run the project checks and report actual results.
11. Do not run migrations against Supabase, push commits, or deploy without explicit approval.

**This document defines the architectural contract for `apps.catalog`.** The separate `catalog_api.md` document must specify the exact endpoint methods, paths, schemas, permissions, filtering behavior, and error responses.