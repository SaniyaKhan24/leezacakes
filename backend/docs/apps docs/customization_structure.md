# Customization App — Architecture and Structure

**Project:** Leeza Cakes  
**Django app:** `apps.customization`  
**Purpose:** Define the architecture, data model, responsibilities, boundaries, and implementation rules for customizable cakes and personalized cake orders.

## 1. Purpose

The `customization` application manages customer-selected cake customizations, including supported flavours, sizes, fillings, frosting options, themes, messages written on cakes, reference images, and customization-specific pricing adjustments.

It defines which customization options are available for a product and validates the selections made by a customer.

The application must support Leeza Cakes' actual business rules. It must not assume that every product supports every customization option.

Customization is a domain application. It must not become a generic configuration engine or duplicate catalogue, cart, order, payment, or media-management responsibilities.

## 2. Scope and Responsibilities

### In scope

- Defining reusable customization option types.
- Defining available choices for each option.
- Associating customization options with eligible products.
- Configuring product-specific allowed choices and constraints.
- Validating customer selections.
- Managing additional charges associated with customization.
- Validating cake inscriptions and special instructions.
- Supporting customer reference images where permitted.
- Producing a normalized, validated representation of a customer's selections.
- Providing administrative management of customization options and rules.
- Preserving the selected customization details when an order is created.

### Out of scope

| Responsibility | Owning application |
|---|---|
| Product names, descriptions, categories, and base prices | `apps.catalog` |
| Customer accounts and profile information | `apps.accounts` |
| Shopping cart and cart line items | `apps.cart` |
| Order lifecycle and order-item snapshots | `apps.orders` |
| Payment processing and payment status | `apps.payments` |
| Email, SMS, and other customer notifications | `apps.notifications` |
| Shared validators, exception handling, and pagination | `apps.common` |
| Product search and indexing | `apps.search` |

The customization application may reference catalogue products through a foreign key, but it must not recreate the product model.

## 3. Architectural Principles

1. **Product-specific eligibility:** A customization is available only when explicitly allowed for the relevant product.
2. **Server-side validation:** Never trust frontend-submitted option IDs, prices, or calculated totals.
3. **Explicit pricing rules:** Every additional charge must follow a documented pricing policy.
4. **Historical consistency:** Once an order is placed, its customization details and prices must not change when catalogue options change.
5. **Reusable options:** Shared options should be reusable across products without forcing every product to use them.
6. **Controlled complexity:** Introduce models only when they represent real business concepts.
7. **Transactional integrity:** Validate and persist related selections consistently.
8. **Least privilege:** Only authorized staff may manage customization definitions and pricing.
9. **Storage boundaries:** Use the configured Django storage backend for uploaded reference images.
10. **Backward compatibility:** Changes to option definitions must not invalidate existing orders.

## 4. Recommended Data Model

The following models are the recommended starting point. Inspect the existing repository before implementation and reuse existing models if equivalent functionality already exists.

### 4.1 `CustomizationOption`

Represents a reusable type of customization.

Examples:

- Flavour
- Cake size
- Filling
- Frosting
- Theme
- Topping
- Inscription
- Dietary preference, if operationally supported

Suggested fields:

| Field | Type | Purpose |
|---|---|---|
| `id` | Primary key | Internal identifier |
| `name` | CharField | Display name |
| `slug` | SlugField | Stable unique identifier |
| `description` | TextField, optional | Customer-facing explanation |
| `input_type` | Choice field | Selection behavior |
| `is_active` | BooleanField | Whether the option can be used |
| `sort_order` | PositiveIntegerField | Display ordering |
| `created_at` | DateTimeField | Creation timestamp |
| `updated_at` | DateTimeField | Last update timestamp |

Supported input types should be limited to actual requirements, such as:

- Single choice
- Multiple choice
- Free text

Do not implement arbitrary dynamic form schemas unless there is a demonstrated business need.

### 4.2 `CustomizationChoice`

Represents an available value for a reusable option.

Examples:

- Chocolate
- Vanilla
- Red velvet
- Buttercream
- Fondant

Suggested fields:

| Field | Type | Purpose |
|---|---|---|
| `id` | Primary key | Internal identifier |
| `option` | ForeignKey | Parent customization option |
| `name` | CharField | Display label |
| `slug` | SlugField | Stable identifier within the option |
| `description` | TextField, optional | Additional information |
| `is_active` | BooleanField | Whether the choice is available |
| `sort_order` | PositiveIntegerField | Display ordering |
| `created_at` | DateTimeField | Creation timestamp |
| `updated_at` | DateTimeField | Last update timestamp |

Enforce uniqueness for the relevant option/slug combination.

A choice being active globally does not automatically make it available for every product.

### 4.3 `ProductCustomization`

Associates a catalogue product with a customization option and defines product-specific rules.

Suggested fields:

| Field | Type | Purpose |
|---|---|---|
| `id` | Primary key | Internal identifier |
| `product` | ForeignKey to catalogue product | Product receiving the customization |
| `option` | ForeignKey | Available customization option |
| `is_required` | BooleanField | Whether the customer must choose a value |
| `is_active` | BooleanField | Whether the option is currently offered for this product |
| `sort_order` | PositiveIntegerField | Display ordering |
| `min_selections` | PositiveIntegerField, optional | Minimum choices for multiple-choice options |
| `max_selections` | PositiveIntegerField, optional | Maximum choices for multiple-choice options |
| `created_at` | DateTimeField | Creation timestamp |
| `updated_at` | DateTimeField | Last update timestamp |

Enforce uniqueness on the product/option relationship unless the business model explicitly requires multiple configurations of the same option for one product.

Validate selection limits against the input type and configured constraints.

### 4.4 `ProductCustomizationChoice`

Associates specific choices with a product customization and stores any product-specific price adjustment.

This model is recommended when the same choice can have different prices or eligibility across products.

Suggested fields:

| Field | Type | Purpose |
|---|---|---|
| `id` | Primary key | Internal identifier |
| `product_customization` | ForeignKey | Product-specific option configuration |
| `choice` | ForeignKey | Reusable choice |
| `price_adjustment` | DecimalField | Additional amount or adjustment, under a defined pricing policy |
| `is_active` | BooleanField | Whether the choice is currently available |
| `sort_order` | PositiveIntegerField | Display ordering |

Enforce uniqueness on the product-customization/choice relationship.

Use `DecimalField`, never floating-point types, for money. Define whether adjustments can be negative, whether they are per cake or per unit, and how they interact with variant pricing before implementation.

### 4.5 `CustomizationSelection`

A normalized selection model may be useful for persistent draft customization sessions or other workflows requiring reusable selection records.

Do not introduce this model automatically.

If selections exist only as part of a cart item and later an order item, the cart and order applications should own their respective selection records or snapshots. The customization application should provide validation and normalization services rather than owning the entire cart/order lifecycle.

If a persistent selection model is required, it must define ownership, lifecycle, expiration, and cleanup behavior explicitly.

### 4.6 Reference images

Customer-uploaded reference images should be associated with the relevant draft customization or cart item through the owning workflow.

Do not store uploaded files as raw binary data in PostgreSQL. Use Django's configured storage backend and persist the storage reference.

Define allowed formats, maximum file size, authorization, retention, and deletion behavior. Do not assume customer reference images may be displayed publicly.

## 5. Relationships

The conceptual relationship is:

- One catalogue product can have many product customization configurations.
- One reusable customization option can be associated with many products.
- One customization option can have many reusable choices.
- A product customization can expose a subset of those choices.
- Each product-specific choice can have its own pricing adjustment.
- A cart item may contain a validated selection snapshot.
- An order item must preserve an immutable snapshot of the selections and their applicable prices.

Use explicit Django relationships and database constraints to enforce valid associations.

Avoid circular imports between Django applications. Use model references and service boundaries appropriately.

## 6. Pricing Rules

Customization pricing must be deterministic and server-authoritative.

Define the following before implementation:

1. Whether an adjustment is a fixed amount per cake, per item, or per selected unit.
2. Whether product variants already include size-related pricing.
3. Whether customization adjustments are additive or replace a base price.
4. Whether discounts apply before or after customization adjustments.
5. How taxes and delivery charges interact with the final total.

A recommended starting formula, if all adjustments are additive, is:

`customized unit price = selected catalogue variant/base price + sum(valid customization adjustments)`

This formula is illustrative and must be adapted to the actual pricing policy. Avoid double-counting size charges when size is already represented by a priced catalogue variant.

The customization app should return validated pricing components to the cart/order workflow. The cart or order pricing service must calculate and validate the final payable amount according to the project's pricing architecture.

Never accept a frontend-computed total as authoritative.

## 7. Validation Service

Provide a clear service boundary for validating selections, for example:

`apps/customization/services/validation.py`

The service should accept a product reference and submitted selections, then validate:

- The product exists and is eligible for customization.
- The product is publicly purchasable where required by the calling workflow.
- Every submitted option belongs to the product's allowed customization configuration.
- Every submitted choice belongs to the submitted option.
- The option and choice are active and available for the product.
- Required options are present.
- Single-choice and multiple-choice constraints are respected.
- Duplicate selections are rejected where not allowed.
- Text fields satisfy length and content constraints.
- Reference images meet upload and ownership requirements.
- Price adjustments are derived from trusted database records.
- The final normalized result is suitable for the cart/order workflow.

The service must return a structured, validated result or raise a documented domain validation error.

Do not rely exclusively on serializer validation. Business rules should also be enforceable from non-HTTP workflows.

## 8. Application Structure

Use the following structure where it fits the existing repository:

```text
apps/
└── customization/
    ├── __init__.py
    ├── admin.py
    ├── apps.py
    ├── models.py
    ├── serializers.py
    ├── selectors.py
    ├── services/
    │   ├── __init__.py
    │   └── validation.py
    ├── permissions.py
    ├── urls.py
    ├── views.py
    ├── exceptions.py
    ├── tests/
    │   ├── __init__.py
    │   ├── test_models.py
    │   ├── test_validation.py
    │   ├── test_api.py
    │   └── test_permissions.py
    └── migrations/
        └── __init__.py
```

Structure rules:

- Keep `models.py` focused on data definitions and database-level invariants.
- Keep serializers responsible for HTTP input/output validation and representation.
- Put reusable business validation in `services/`.
- Use `selectors.py` for complex reusable read queries when beneficial.
- Keep views thin.
- Use explicit permissions for administrative endpoints.
- Keep API versioning and route conventions consistent with the rest of the project.
- Do not create empty modules merely to match this tree.
- A single model or service file is sufficient until the application grows enough to justify further separation.

## 9. API Boundary

The public API contract is specified separately in `customization_api.md`.

At a high level, the application may expose:

- Public customization options available for a product.
- Product-specific available choices and price adjustments.
- Validation of proposed customization selections, if required by the frontend workflow.
- Administrative management of options, choices, product associations, and pricing.

Public reads must expose only active, eligible options and choices for publicly available products.

Administrative writes require appropriate staff permissions.

The cart and order applications must use the same server-side validation and pricing rules as the public API. API validation must not be the only enforcement mechanism.

## 10. Integration Boundaries

### Catalog

`apps.catalog` owns product identity, product publication, product variants, and base pricing.

Customization may reference catalogue products and variants but must not duplicate their definitions.

If catalogue variants represent cake sizes, avoid creating a second competing size-pricing system in customization.

### Cart

`apps.cart` owns cart items and the current cart state.

The customization app validates submitted selections. The cart must retain a validated representation of those selections and recalculate pricing whenever relevant cart data changes.

A selection valid yesterday may no longer be purchasable today. Revalidate at the appropriate transaction boundaries.

### Orders

`apps.orders` owns order items and historical snapshots.

When an order is created, snapshot at least:

- Selected option names.
- Selected choice names or values.
- Relevant customer-entered inscription or instructions.
- Applicable pricing adjustments.
- Currency.
- Final customization-related amounts.

Order history must remain correct even if staff rename, deactivate, or reprice an option later.

### Accounts

Use the authenticated account or the owning cart/order workflow for authorization. Do not duplicate customer identity or profile fields in customization.

### Notifications

The customization application does not send emails or SMS directly. Notifications belong to `apps.notifications` and should be triggered through the established workflow.

### Common

Use shared error handling, validators, pagination, and response conventions from `apps.common` where appropriate.

## 11. Security and Data Integrity

- Require staff permissions for customization administration.
- Validate product, option, and choice ownership on every write.
- Do not trust IDs or prices supplied by the frontend.
- Prevent unauthorized users from reading or modifying another customer's private draft selections or uploads.
- Validate uploads by actual content and permitted file type, not filename alone.
- Enforce database uniqueness and appropriate foreign-key behavior.
- Use transactions for operations that update multiple related records.
- Prevent inactive or invalid choices from entering newly submitted carts/orders.
- Avoid hard deletion of records referenced by historical orders.
- Never expose internal storage paths, server filesystem paths, or exception traces.
- Apply reasonable text length limits to inscriptions and instructions.
- Do not interpret customer-provided reference images or text as trusted operational instructions.

## 12. Testing Strategy

Tests must cover the following areas.

### Models

- Required fields and defaults.
- Slug and relationship uniqueness.
- Valid product/option/choice associations.
- Valid price precision and constraints.
- Active/inactive behavior.
- Foreign-key deletion policies.

### Validation service

- Valid selections.
- Missing required selections.
- Invalid option IDs and choice IDs.
- Choices belonging to the wrong option.
- Choices not enabled for the selected product.
- Duplicate selections.
- Single-choice and multiple-choice limits.
- Invalid text length.
- Price adjustments derived from database records.
- Inactive products and choices.
- Correct handling of variants and size pricing.

### API

- Public users can read eligible active options.
- Inactive and ineligible choices are hidden.
- Invalid selections return consistent validation errors.
- Administrative writes require the correct permissions.
- Unsupported methods and malformed payloads are handled correctly.
- API schemas accurately represent request and response formats.

### Workflow integration

- Cart pricing uses validated customization selections.
- Price changes trigger the appropriate cart revalidation.
- Orders preserve immutable customization snapshots.
- Deactivated options do not corrupt historical orders.
- Upload authorization and deletion behavior are enforced.

Tests must use isolated test data and must not modify production Supabase records.

## 13. Implementation Order

1. Inspect existing catalogue models and determine whether product variants already represent cake sizes.
2. Finalize customization pricing semantics and supported input types.
3. Implement the minimum required models and database constraints.
4. Implement the reusable validation service.
5. Add administrative management and permissions.
6. Implement the public and administrative API according to `customization_api.md`.
7. Integrate validated selections with the cart.
8. Integrate immutable snapshots with orders.
9. Add tests for models, validation, permissions, pricing, and workflow integration.
10. Verify OpenAPI documentation and full-suite compatibility.

Do not implement the cart or order workflow inside the customization application.

## 14. Definition of Done

The customization foundation is complete when:

- The models represent the agreed business concepts without duplicating catalogue functionality.
- Product-specific option eligibility is enforced.
- Pricing adjustments are validated and calculated server-side.
- Shared validation logic is reusable outside HTTP views.
- Administrative endpoints enforce permissions.
- Public endpoints expose only eligible options and choices.
- Cart and order integration boundaries are documented and tested.
- Historical order snapshots are immutable.
- Tests, Ruff, and Django checks pass.
- OpenAPI documentation matches the implemented API.
- No secrets, production records, or unrelated applications are modified.

## 15. Decisions Requiring Confirmation

Before implementation, resolve these points against Leeza Cakes' actual product workflow:

1. **Size selection:** Is cake size a catalogue variant or a customization option? Prefer a catalogue variant if each size has its own base price.
2. **Flavours and fillings:** Can customers choose one flavour or multiple flavours for a single cake?
3. **Pricing:** Are customization charges fixed, per unit, or dependent on cake size?
4. **Inscription:** Is cake text a dedicated free-text field or a reusable option?
5. **Reference images:** Are uploads needed, and how long should they be retained?
6. **Customization persistence:** Should selections be stored only on cart/order items, or should the application support reusable draft customization sessions?
7. **Administrative workflow:** Are staff approval or product-specific publication rules required?

Do not invent business requirements for unresolved decisions. Document the agreed choices before implementing models and migrations.