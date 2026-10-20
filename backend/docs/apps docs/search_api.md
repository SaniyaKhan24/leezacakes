# Search API — Leeza Cakes

**File:** `backend/docs/apps/search_api.md`  
**Backend:** Django + Django REST Framework  
**API version:** v1  
**Database:** PostgreSQL  
**Status:** API specification; implementation pending

## 1. Purpose

The Search API allows customers to discover cakes and accessories using product names, categories, descriptions, colours, occasions, flavours, and other searchable catalogue attributes.

The API uses PostgreSQL-backed hybrid search combining:

- Exact and partial text matching.
- Full-text relevance ranking.
- Approved synonyms.
- Structured catalogue attributes.
- Price, product-type, category, and availability filters.
- Related-result fallback when exact matches are insufficient.

Search results must contain only products eligible for public discovery. The `catalog` app remains the source of truth for product information, images, variants, prices, publication, and availability.

## 2. Base URL and conventions

Base path:

`/api/v1/search/`

HTTP method: `GET`

Authentication: Not required for ordinary public product search.

Content type: `application/json`

The API uses the project's standard pagination and error-response conventions. Query parameters must be validated before they reach the search service.

All prices are in INR for the initial launch. The API must not accept arbitrary currency values or interpret amounts as another currency.

## 3. Primary endpoint

### Search products

`GET /api/v1/search/`

This endpoint searches cakes and accessories together unless the customer supplies a product-type filter.

Example requests:

```http
GET /api/v1/search/?q=pink%20birthday%20cake
GET /api/v1/search/?q=blue%20cake&color=blue
GET /api/v1/search/?q=wedding%20cake&occasion=wedding
GET /api/v1/search/?q=chocolate%20cake&flavour=chocolate
GET /api/v1/search/?q=birthday%20candles&product_type=accessory
GET /api/v1/search/?q=cake&min_price=500&max_price=1500
GET /api/v1/search/?q=anniversary%20cake&sort=relevance&page=1&page_size=20
```

These are illustrative requests. Filter values must match the canonical catalogue identifiers.

## 4. Query parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `q` | String | No | Search phrase |
| `category` | String | No | Category slug or supported identifier |
| `product_type` | String | No | Catalogue-defined product type, such as `cake` or `accessory` |
| `occasion` | String | No | Configured occasion identifier |
| `color` | String | No | Configured colour identifier |
| `flavour` | String | No | Configured flavour identifier |
| `min_price` | Decimal | No | Minimum eligible price |
| `max_price` | Decimal | No | Maximum eligible price |
| `available` | Boolean | No | Restrict results to products available for purchase |
| `sort` | String | No | Result ordering; defaults to `relevance` |
| `page` | Integer | No | Page number; defaults to `1` |
| `page_size` | Integer | No | Results per page; defaults to `20`, subject to a configured maximum |
| `include_facets` | Boolean | No | Include facet counts; defaults to `true` |

### 4.1 Query behavior

The `q` parameter supports free-text searches such as:

- `girls birthday cake`
- `cake for boys`
- `pink and white cake`
- `red velvet anniversary cake`
- `gold cake topper`
- `balloons`
- `chocolate cake under 1500`

When structured intent is confidently recognized, the service may extract it into filters or relevance boosts. Unrecognized words must remain available for text matching.

A parsed expression must not silently override an explicit query parameter. If a query expression conflicts with an explicit filter, the API should return a validation error or follow one documented, consistent precedence rule. The recommended initial policy is to reject contradictory price constraints.

### 4.2 Price validation

- Prices must be non-negative decimal values.
- `min_price` must not exceed `max_price`.
- Currency is INR.
- Invalid numeric values must return a validation error.
- Price filtering must use the catalogue's authoritative price model.

For products with differently priced variants, filtering must follow the catalogue's defined eligible-price policy. Search must not imply that a displayed starting price is the final price for every variant.

### 4.3 Boolean validation

The `available` and `include_facets` parameters must accept only documented boolean representations supported by the API, such as `true` and `false`.

Invalid boolean values must not be silently interpreted as `false`.

### 4.4 Sorting

Supported values:

- `relevance`: best match first; default when a text query is supplied.
- `price_asc`: eligible price from low to high.
- `price_desc`: eligible price from high to low.
- `newest`: newest eligible products first, where the catalogue provides a suitable timestamp.

Unsupported sort values must return a validation error.

Sorting must be deterministic, using a stable secondary key where needed for consistent pagination.

## 5. Search response

Example:

```json
{
  "query": "pink birthday cake",
  "normalized_query": "pink birthday cake",
  "count": 2,
  "page": 1,
  "page_size": 20,
  "sort": "relevance",
  "applied_filters": {
    "product_type": "cake",
    "color": "pink"
  },
  "fallback_used": false,
  "results": [
    {
      "id": "product-id-1",
      "name": "Pink Floral Birthday Cake",
      "slug": "pink-floral-birthday-cake",
      "product_type": "cake",
      "category": {
        "slug": "birthday-cakes",
        "name": "Birthday Cakes"
      },
      "primary_image": "https://example.com/product-image.jpg",
      "price": {
        "amount": "1200.00",
        "currency": "INR",
        "display_type": "starting_from"
      },
      "available": true,
      "match_type": "direct"
    }
  ],
  "facets": {
    "categories": [
      {
        "value": "birthday-cakes",
        "label": "Birthday Cakes",
        "count": 2
      }
    ],
    "product_types": [
      {
        "value": "cake",
        "label": "Cakes",
        "count": 2
      }
    ],
    "colors": [
      {
        "value": "pink",
        "label": "Pink",
        "count": 2
      }
    ],
    "occasions": [],
    "flavours": []
  },
  "suggestions": []
}
```

All identifiers, products, URLs, prices, counts, and values in this example are illustrative.

### 5.1 Response fields

| Field | Meaning |
|---|---|
| `query` | Original query supplied by the client, if present |
| `normalized_query` | Normalized text used for matching |
| `count` | Total count for the result set under the documented pagination strategy |
| `page` | Current page |
| `page_size` | Requested or effective page size |
| `sort` | Effective sort mode |
| `applied_filters` | Validated structured filters |
| `fallback_used` | Whether related-result fallback was used |
| `results` | Ranked product summaries |
| `facets` | Available facet groups and counts, or an empty object when disabled |
| `suggestions` | Optional relevant category or query suggestions |

The implementation may use the project's established pagination envelope instead of the illustrative `count`, `page`, and `page_size` fields, provided the contract remains consistent.

### 5.2 Product result fields

Each result should include only the data required by the product-card experience:

- `id`: canonical catalogue product identifier.
- `name`: product name.
- `slug`: canonical product slug, if available.
- `product_type`: catalogue-defined product type.
- `category`: optional category summary.
- `primary_image`: canonical public image URL or the project's established image representation.
- `price`: display price and currency.
- `available`: public availability state.
- `match_type`: optional indicator of why the product was returned.

The serializer must use actual catalogue model fields. It must not assume the example schema exists unchanged.

For variable-price products, `display_type` may distinguish `starting_from` from a fixed price. The frontend must not represent a starting price as the final price of a selected variant.

## 6. Unified cakes and accessories

The endpoint must return cakes and accessories using the same result structure.

Examples:

- `q=birthday cake` should prioritize relevant cakes.
- `q=birthday candles` should prioritize relevant accessories.
- `q=balloons` should return matching catalogue accessories.
- An unfiltered query may return both types, ranked by relevance.

The `product_type` filter restricts results to the canonical product type represented in the catalogue.

Search must not invent product types or return unpublished accessories merely because their names match the query.

## 7. Structured filters

### 7.1 Category

`category` restricts results to a valid catalogue category.

Category values should use the canonical identifier or slug defined by the catalogue API. Unknown categories must be handled consistently as validation errors or empty results according to the established API convention.

### 7.2 Occasion

`occasion` matches configured catalogue occasion attributes.

Examples include `birthday`, `wedding`, and `anniversary`, where those values exist.

The service may also use relevant occasion terms in descriptions for ranking, but a description match must not be represented as a verified structured attribute.

### 7.3 Colour

`color` matches configured colour attributes and may be supplemented by description matching when appropriate.

For combined-colour queries, the parser should prefer products matching all requested colours when the catalogue can represent those colours reliably.

If the structured catalogue cannot verify a combined-colour condition, the service must not falsely claim that the structured filter was satisfied.

### 7.4 Flavour

`flavour` matches the catalogue's configured flavour attributes.

The API must use the catalogue's canonical spelling and identifier conventions.

### 7.5 Availability

`available=true` restricts results to products considered available according to catalogue rules.

Availability must not be inferred solely from a product's publication status.

Search must not guarantee that a product remains available at checkout. Cart and checkout must revalidate the current product, variant, price, and availability.

## 8. Facets

When `include_facets=true`, return relevant facet groups based on the current query and documented filtering semantics.

Supported facet groups may include:

- `categories`
- `product_types`
- `colors`
- `occasions`
- `flavours`
- Price ranges, if implemented.

Each facet item should contain:

- `value`: canonical identifier.
- `label`: customer-facing label.
- `count`: number of matching products under the facet-counting policy.

Facet counts should reflect published, publicly eligible catalogue products. The recommended behavior is to compute each facet while excluding that facet's own selected filter, allowing customers to see alternative filter choices.

The API must avoid expensive per-result queries when calculating facets.

When `include_facets=false`, return an empty facets object or omit the field according to the project's chosen response convention. Use one convention consistently.

## 9. Related-result fallback

If exact matches are absent or insufficient, the service may return relevant alternatives.

Recommended fallback order:

1. Approved synonym expansion.
2. Partial or typo-tolerant matching where configured.
3. Related products in the same category.
4. Products sharing the requested occasion, colour, or flavour.
5. Relevant category suggestions.

The `fallback_used` field must indicate when fallback retrieval was applied.

Individual results may use `match_type` values such as:

- `direct`
- `synonym`
- `related`

These are proposed values and must be finalized before implementation.

Fallback behavior must preserve explicit constraints, including:

- Price limits.
- Product-type filters.
- Category filters.
- Publication eligibility.
- Availability constraints when explicitly requested.

If no relevant products exist, return an empty `results` array and optional useful category suggestions.

The API must not fill an empty result set with unrelated products simply to display something.

## 10. Empty query behavior

When `q` is absent or blank, the API may return a default browse listing if required by the storefront.

The initial behavior should be aligned with the frontend's intended browse experience.

Any default listing must:

- Use a bounded, deterministic query.
- Exclude unpublished products.
- Apply supplied structured filters.
- Avoid scanning and serializing the entire catalogue.
- Use a documented default sort.

An empty query must not accidentally trigger expensive fuzzy search or related-result fallback across the entire catalogue.

## 11. Optional autocomplete endpoint

Autocomplete is not required for launch.

If the frontend later needs search suggestions while typing, consider:

`GET /api/v1/search/suggestions/?q=birt`

Example response:

```json
{
  "query": "birt",
  "suggestions": [
    {
      "type": "category",
      "label": "Birthday Cakes",
      "slug": "birthday-cakes"
    },
    {
      "type": "product",
      "label": "Birthday Chocolate Cake",
      "slug": "birthday-chocolate-cake"
    }
  ]
}
```

The values are illustrative.

Autocomplete must use a small result limit, public catalogue visibility rules, and a lightweight query path. It should not calculate full facet counts.

Do not implement this endpoint unless it is needed by the frontend.

## 12. Validation and error responses

The API must use the project's standard error envelope. The following examples are illustrative.

### Invalid price range

HTTP `400 Bad Request`

```json
{
  "detail": "min_price cannot exceed max_price.",
  "code": "validation_error"
}
```

### Invalid sort value

HTTP `400 Bad Request`

```json
{
  "detail": "Unsupported sort option.",
  "code": "validation_error",
  "errors": {
    "sort": ["Use a supported sort value."]
  }
}
```

### Invalid pagination

HTTP `400 Bad Request`

```json
{
  "detail": "Invalid pagination parameters.",
  "code": "validation_error"
}
```

### Empty search result

HTTP `200 OK`

```json
{
  "query": "unmatched product phrase",
  "count": 0,
  "results": [],
  "facets": {
    "categories": [],
    "product_types": [],
    "colors": [],
    "occasions": [],
    "flavours": []
  },
  "fallback_used": false,
  "suggestions": []
}
```

An empty result is not an API error.

The exact envelope must follow the existing project conventions. Do not introduce a conflicting error format just for search.

## 13. Security and visibility

- Search must return only published products eligible for public discovery.
- Draft and archived products must remain hidden.
- Validate and bound the query length.
- Validate all filters and pagination parameters.
- Use Django ORM and parameterized query construction.
- Allowlist sort options.
- Never interpolate raw user input into SQL.
- Do not expose internal catalogue fields, costs, staff notes, or private records.
- Apply rate limiting if needed to control abuse and expensive query patterns.
- Do not expose private customer information through search.
- Treat product descriptions as untrusted data when rendering or serializing them.
- Use canonical catalogue URLs and identifiers.

Search is not a purchase authorization mechanism. The cart and checkout must independently validate product visibility, current pricing, variant selection, and customization constraints.

## 14. Performance requirements

The implementation should:

- Use bounded pagination.
- Avoid loading the full catalogue into Python.
- Avoid N+1 queries.
- Use `select_related` and `prefetch_related` where appropriate.
- Calculate facets efficiently.
- Use PostgreSQL full-text search for text relevance.
- Add substring or trigram matching selectively.
- Use deterministic ordering.
- Evaluate actual query plans before adding indexes.
- Measure performance against representative catalogue volumes.

`pg_trgm` may be used for typo tolerance only after its availability, permissions, indexes, and performance have been verified in the target PostgreSQL environment.

Do not add Elasticsearch, OpenSearch, a vector database, or a separate search-index database for the initial implementation.

## 15. Testing requirements

Automated API tests must cover:

### Query behavior

- Product-name matching.
- Category matching.
- Description matching.
- Synonym expansion.
- Case and whitespace normalization.
- Colour, occasion, and flavour matching.
- Price expression parsing.
- Combined cakes-and-accessories results.

### Filters and sorting

- Category and product-type filters.
- Colour, occasion, and flavour filters.
- Minimum and maximum price.
- Availability.
- Relevance and price sorting.
- Invalid filters and contradictory price constraints.
- Stable pagination.

### Facets and fallback

- Accurate facet counts.
- Selected-filter facet semantics.
- No unrelated fallback products.
- Related products preserve explicit price and availability constraints.
- Empty-result responses are valid.
- Unpublished products never appear in results or facets.

### Security and performance

- Anonymous search works as intended.
- Raw input cannot alter SQL structure.
- Query length and page-size limits are enforced.
- Internal catalogue fields are not exposed.
- N+1 query regressions are checked where practical.
- Representative queries are tested against a suitable test database.

All tests must use controlled test data. Do not run tests that mutate production catalogue records.

## 16. Implementation order

1. Inspect the existing catalogue schema and API response conventions.
2. Confirm canonical product types, categories, colours, occasions, and flavours.
3. Implement query parameter validation.
4. Implement the search service and query normalization.
5. Add structured filters and PostgreSQL full-text ranking.
6. Add approved synonyms and selected partial matching.
7. Implement unified product serialization.
8. Add pagination and deterministic sorting.
9. Implement facets and related-result fallback.
10. Add tests for ranking, filtering, visibility, and performance.
11. Integrate the frontend.
12. Tune ranking weights against representative real catalogue products.
13. Document any schema changes separately before implementation.

## 17. Explicitly undecided items

| Item | Status |
|---|---|
| Exact catalogue fields and canonical identifiers | Must be inspected |
| Variant-price aggregation policy | Must be finalized |
| Empty-query browse behavior | Frontend-dependent |
| Exact relevance weights | Requires evaluation |
| Typo-tolerance threshold | Requires evaluation and optional `pg_trgm` support |
| Combined-colour matching semantics | Recommended all-colours matching when supported |
| Final facet-counting implementation | Recommended self-excluding facets |
| Autocomplete | Optional |
| Search analytics | Not required for launch |

## 18. Acceptance criteria

The Search API is ready when:

- One endpoint searches cakes and accessories.
- Text and structured attributes both contribute to matching.
- Exact and strong matches rank above incidental description matches.
- Filters operate against authoritative catalogue data.
- Facets reflect documented filtering semantics.
- Related results remain relevant and respect explicit constraints.
- Only eligible published products are returned.
- Pagination and sorting are stable.
- API validation and error handling follow project conventions.
- Automated tests cover search behavior, visibility, filters, facets, and performance.
- The frontend can navigate to canonical catalogue product pages.
- Cart and checkout independently revalidate purchase conditions.

**Final rule:** Search discovers and ranks catalogue products. It does not own product data, authorize purchases, or guarantee that a product's price or availability will remain unchanged after the search response.