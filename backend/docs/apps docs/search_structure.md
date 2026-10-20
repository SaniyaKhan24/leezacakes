# Search App — Structure and Architecture

**Project:** Leeza Cakes  
**Backend:** Django + Django REST Framework  
**Database:** PostgreSQL (Supabase)  
**Document:** `backend/docs/apps/search_structure.md`  
**Status:** Architecture specification; implementation pending

---

## 1. Purpose

The `search` app provides a unified product discovery system for the Leeza Cakes storefront.

Customers must be able to search for cakes, accessories, categories, occasions, colours, flavours, and relevant product details using natural, varied search phrases.

Example queries include:

- `girls birthday cake`
- `cake for boys`
- `wedding cake`
- `anniversary cake`
- `pink cake`
- `blue and white cake`
- `chocolate cake`
- `chocolate cake under 1500`
- `red velvet cake for anniversary`
- `balloons`
- `birthday candles`
- `golden cake topper`
- `cake with floral design`
- `custom photo cake`

Search must return relevant, published, purchasable catalogue items first, apply the requested filters correctly, and provide useful alternatives when no exact match exists.

The initial implementation will use PostgreSQL and Django ORM. It will not introduce Elasticsearch or another external search engine. Semantic embeddings are not required for the initial version.

## 2. Confirmed decisions

| Area | Decision |
|---|---|
| Search coverage | Products, categories, descriptions, colours, flavours, occasions, and product attributes |
| Search method | Hybrid search combining structured filters, exact matches, partial matches, and weighted text relevance |
| Colour matching | Structured product attributes plus searchable descriptions |
| Product types | Cakes and accessories through one unified search API |
| Filters | Category, product type, occasion, colour, flavour, price range, availability, and sorting |
| Results | Ranked products with relevant facet counts |
| No exact match | Return relevant alternatives and related category suggestions where possible |
| Database/search engine | PostgreSQL and Django ORM |
| External search engine | Not required for launch |
| Product data ownership | `catalog` remains the source of truth |
| Migrations | Not authorized by this document |

## 3. Scope and responsibilities

### 3.1 Responsibilities owned by `search`

The app owns:

- Search query normalization.
- Search-term parsing and supported synonym expansion.
- Searchable-field selection.
- Search ranking and relevance scoring.
- Query construction and execution.
- Search filters and sorting.
- Pagination.
- Facet aggregation.
- Related-result selection when exact matches are unavailable.
- Search-specific performance optimization.
- Search telemetry where explicitly approved and privacy-safe.

### 3.2 Responsibilities outside `search`

The app must not:

- Create or edit products, categories, variants, or product images.
- Own catalogue prices or stock.
- Decide whether a product is published.
- Maintain a separate authoritative product database.
- Create cart items or orders.
- Validate customization selections for checkout.
- Calculate final order totals.
- Manage customer notifications.
- Own product-specific business rules.

`catalog` owns product information. `search` retrieves and ranks it.

Search results are discovery results, not authorization to purchase a product. The cart and checkout workflows must revalidate product publication, current price, availability, variants, and customization rules.

## 4. App boundaries and dependencies

### 4.1 `catalog`

The catalogue owns the authoritative data for:

- Products.
- Categories.
- Product types.
- Descriptions.
- Product images.
- Variants and sizes.
- Prices and currencies.
- Publication status.
- Availability.
- Structured attributes, including colours, flavours, and occasions where implemented.

Search should query these models directly or through catalogue-owned query helpers.

The `search` app must not introduce a second `Product`, `Category`, or `ProductVariant` model.

### 4.2 `customization`

`customization` owns product-specific options and allowed choices.

Examples include inscriptions, supported decoration choices, and other product-specific customization options.

Search may use selected, explicitly searchable customization metadata when it helps discovery. It must not assume that a customer can order an arbitrary option merely because that term matches a product description.

### 4.3 `cart`

`cart` owns cart contents and cart validation.

Search can link a result to a product detail page, but it must not directly add an item to the cart or bypass variant and customization validation.

### 4.4 `orders` and `payments`

These apps do not depend on search for business-critical decisions.

Search does not determine order status, payment verification, or historical order values.

### 4.5 `accounts`

Search may operate for anonymous visitors and authenticated customers.

Customer authentication must not be required for ordinary product discovery unless a separate business requirement establishes restricted catalogue access.

Search must not expose private customer information or personalized data without an explicitly approved feature.

### 4.6 `common`

Use shared infrastructure for standard API responses, exceptions, pagination conventions, and other established project-wide utilities where appropriate.

Search-specific parsing, ranking, and filter behavior belong in `search`.

### 4.7 Dependency direction

Recommended flow:

`Frontend → Search API → Search service → Catalogue query layer → PostgreSQL`

The search service returns ranked catalogue results. The frontend navigates to the canonical product detail page for authoritative product information.

Avoid circular imports between `catalog` and `search`. If catalogue queries need to reuse search logic, define a stable interface rather than making catalogue depend on search-specific implementation details.

---

## 5. Search architecture

The initial search pipeline should consist of the following stages:

1. Validate the query and filters.
2. Normalize the query.
3. Identify known product attributes, categories, and search synonyms.
4. Parse supported price expressions and structured filters.
5. Build the candidate catalogue queryset.
6. Apply publication and availability constraints.
7. Calculate text relevance and exact-match boosts.
8. Apply user-requested filters.
9. Order results by relevance or the requested sort.
10. Calculate facet counts from the appropriate filtered queryset.
11. Paginate results.
12. If appropriate, retrieve related alternatives or category suggestions.
13. Serialize the response using the standard API contract.

This pipeline should be implemented as small, testable services rather than one large API view.

### 5.1 Query normalization

Normalize user input before matching:

- Trim leading and trailing whitespace.
- Collapse repeated whitespace.
- Normalize case for case-insensitive matching.
- Normalize equivalent spacing and punctuation where appropriate.
- Preserve meaningful terms such as product names, sizes, and numeric price expressions.
- Handle common spelling variations and approved synonyms.
- Avoid removing words that materially change the query.

For example:

`"  PINK   Birthday Cake "` becomes `"pink birthday cake"` for matching.

Normalization must not alter the original user-facing query unnecessarily.

### 5.2 Synonym expansion

Use a controlled synonym dictionary for common customer terminology.

Examples:

| Customer term | Possible matching terms |
|---|---|
| `bday` | `birthday` |
| `b'day` | `birthday` |
| `anniv` | `anniversary` |
| `baloons` | `balloons` |
| `baloons` | `balloon` |
| `cake topper` | `cake topper`, `cake decoration` |
| `girls cake` | Products tagged with relevant birthday or design attributes, where those attributes exist |
| `boys cake` | Products tagged with relevant birthday or design attributes, where those attributes exist |

Synonyms must be reviewed and maintained as product vocabulary evolves. They should not produce misleading matches merely because two phrases are associated with the same occasion.

For example, `girls cake` should not automatically mean every pink cake, and `boys cake` should not automatically mean every blue cake. These are intent hints, not universal colour rules.

The synonym dictionary must be deterministic, testable, and independent of any particular external search engine.

### 5.3 Search intent and structured extraction

The search service may recognize supported concepts such as:

- Product type: cake or accessory.
- Occasion: birthday, wedding, anniversary, and other configured occasions.
- Colour: pink, blue, red, white, black, gold, and other configured values.
- Flavour: chocolate, vanilla, red velvet, and other configured values.
- Price expressions: under a specified amount, above a specified amount, or within a range.
- Product category and known catalogue attributes.

Structured extraction should only activate filters when the interpretation is sufficiently clear.

For example, `pink cake under 1500` can be interpreted as a cake query with a pink-colour constraint and a maximum price.

The implementation must not assume that every word maps to a known attribute. Unrecognized words should remain part of the text query instead of being silently discarded.

If the parser cannot reliably interpret an expression, preserve it as search text and allow the customer to apply explicit filters.

---

## 6. Hybrid search and ranking

Hybrid search combines structured matching and text relevance. It does not require an external vector database or a separate search engine.

### 6.1 Candidate matching

The search query should consider available catalogue fields, including:

- Product name.
- Category name and hierarchy.
- Short description.
- Full description.
- Product type.
- Configured occasion attributes.
- Configured colour attributes.
- Configured flavour attributes.
- Other explicitly searchable product metadata.

Only fields that actually exist in the catalogue schema may be queried. Where structured attributes have not yet been implemented, search can use description and name matching until those fields become available.

### 6.2 Relevance ranking

The default ordering should prioritize relevance, not simply newest products or cheapest prices.

A recommended priority order is:

1. Exact product-name match.
2. Exact category or product-type match.
3. Strong match against the principal query terms in the product name.
4. Match against structured attributes explicitly requested by the customer.
5. Match against configured synonyms.
6. Match against descriptions and supporting searchable fields.
7. Partial or prefix matches.
8. Relevant alternatives when direct matches are insufficient.

The final scoring implementation may combine PostgreSQL full-text rank, exact-match boosts, and structured attribute boosts.

Illustrative scoring model:

`final_score = text_relevance + exact_name_boost + category_boost + attribute_match_boost + synonym_match_boost`

This formula describes the intended ranking behavior, not finalized numeric weights.

The numeric weights must be tuned using representative catalogue products and realistic customer queries. Avoid assigning fixed values without evaluation.

### 6.3 PostgreSQL capabilities

Use PostgreSQL features appropriate to the installed database and Django version:

- `SearchVector`, `SearchQuery`, and `SearchRank` for full-text matching.
- `icontains` or equivalent case-insensitive matching for selected fallback cases.
- `TrigramSimilarity` for typo tolerance where the PostgreSQL `pg_trgm` extension is available and configured.
- Database indexes for frequently used filters.
- Django ORM annotations and expressions for relevance scoring.

Trigram matching should be optional until the extension is verified. Do not assume that enabling the Django extension package automatically enables the PostgreSQL extension in the target database.

Full-text search and substring matching solve different problems. Use full-text ranking for relevance, with targeted substring or trigram matching for names and short queries where it adds measurable value.

### 6.4 Price expressions

Where the parser recognizes an explicit price expression, it should convert the amount into a structured filter.

Examples:

- `under 1500` → maximum price.
- `above 1000` → minimum price.
- `between 1000 and 2000` → minimum and maximum price.

Leeza Cakes uses INR at launch.

Prices must use the authoritative catalogue pricing model. If a product has variants with different prices, the implementation must define which price is used for search filtering and display.

Recommended initial behavior:

- Display a clear starting price when variant prices vary.
- Match the product when at least one eligible purchasable variant satisfies the requested price range.
- Avoid treating the starting price as the final price of every variant.
- Revalidate the exact variant price in the cart and checkout workflow.

The exact variant-price aggregation policy must be confirmed during catalogue integration.

---

## 7. Colour, occasion, and flavour search

### 7.1 Structured attributes plus descriptions

Colour, occasion, and flavour searches must use both structured catalogue data and searchable text.

Structured attributes are preferred for reliable filtering because they are consistent and machine-readable. Description matching provides useful coverage for existing product descriptions that mention attributes not yet structured.

For example, a customer searching for `blue birthday cake` should be able to match a product through:

- A configured blue colour attribute.
- A configured birthday occasion attribute.
- Relevant name or description terms.

A product should not be classified as blue solely because the word appears in an unrelated sentence or negated statement. Structured attributes should receive higher ranking weight than incidental text matches.

### 7.2 Data quality dependency

The search service cannot reliably infer every product attribute from arbitrary prose.

For accurate colour, occasion, and flavour filtering, the catalogue should gradually adopt controlled values and relationships for those attributes.

Examples:

- `pink`
- `blue`
- `gold`
- `birthday`
- `wedding`
- `anniversary`
- `chocolate`
- `vanilla`
- `red_velvet`

Use normalized identifiers or slugs for filtering, with customer-friendly labels for display.

Do not hard-code these example values as the complete catalogue vocabulary. The actual available values should come from catalogue data.

### 7.3 Combined colour queries

A query such as `pink and white cake` may imply multiple colours rather than a choice between them.

The implementation must define whether combined colour terms mean:

- All requested colours must be present.
- Any requested colour may match.
- The terms are only text-ranking hints.

Recommended behavior: when the parser confidently identifies a combined-colour request, prefer products matching all requested structured colours. If the schema cannot represent multiple colours for a product, fall back to text relevance without pretending that the structured condition was verified.

---

## 8. Unified cakes and accessories search

Cakes and accessories must be searchable through the same API.

Examples of accessories include:

- Balloons.
- Birthday candles.
- Cake toppers.
- Cake decorations.
- Other catalogue-managed add-ons.

Search must not assume that every non-cake product is an accessory. Product type and category must be determined by catalogue data.

### 8.1 Product-type filtering

The API should support an explicit product-type filter, using values defined by the catalogue schema.

For example:

`product_type=cake`

or:

`product_type=accessory`

These are illustrative values. The final values must match the canonical catalogue model.

When no product-type filter is supplied, return relevant cakes and accessories together, ranked by query relevance.

For `birthday candles`, accessories should rank ahead of cakes because the query specifically describes an accessory.

For `birthday cake`, cake products should rank ahead of accessories.

### 8.2 Shared result shape

The API should use a consistent result schema for both cakes and accessories.

Product-specific information may be represented by a type field and a canonical detail URL. Avoid forcing every product into a cake-specific response model.

For example, cake results may have variants and cake customizations, while accessories may have a simpler purchase structure.

The search response must not assume that all products support the same customization fields.

---

## 9. Search filters

The search API should support the following filters where the catalogue schema contains the corresponding fields.

| Filter | Purpose |
|---|---|
| `category` | Restrict results to a category or supported category identifier |
| `product_type` | Restrict results to cakes, accessories, or another configured type |
| `occasion` | Match configured occasion attributes |
| `color` | Match configured colour attributes |
| `flavour` | Match configured flavour attributes |
| `min_price` | Minimum eligible product price |
| `max_price` | Maximum eligible product price |
| `available` | Filter according to the catalogue's authoritative availability representation |
| `sort` | Select an approved ordering |

### 9.1 Filter semantics

- Invalid filter values must return a validation error or be rejected according to the project's standard conventions.
- Minimum price cannot exceed maximum price.
- Prices must be non-negative.
- Pagination limits must be bounded.
- Filters must not expose unpublished products.
- Availability must use the canonical catalogue definition.
- Sorting options must be allowlisted; never interpolate arbitrary client values into database expressions.

### 9.2 Sorting

Recommended supported options:

- `relevance`: default for text searches.
- `price_asc`: eligible price from low to high.
- `price_desc`: eligible price from high to low.
- `newest`: newest eligible products first, if catalogue timestamps support this.

When a customer explicitly requests a price sort, apply the selected sort instead of silently reverting to relevance. Use deterministic secondary ordering to keep pagination stable.

A popularity sort is not required for launch unless a reliable popularity metric is available and approved.

---

## 10. Facets and related results

### 10.1 Facets

Facets help customers narrow search results without submitting a completely new search manually.

Potential facet groups:

- Categories.
- Product types.
- Occasions.
- Colours.
- Flavours.
- Price ranges, if supported by the catalogue's price model.

Example response structure:

```json
{
  "facets": {
    "categories": [
      {
        "value": "birthday-cakes",
        "label": "Birthday Cakes",
        "count": 12
      }
    ],
    "product_types": [
      {
        "value": "cake",
        "label": "Cakes",
        "count": 18
      },
      {
        "value": "accessory",
        "label": "Accessories",
        "count": 4
      }
    ],
    "colors": [
      {
        "value": "pink",
        "label": "Pink",
        "count": 7
      }
    ]
  }
}
```

Counts are illustrative.

Facet counts must be based on the intended candidate and filter set, with semantics documented consistently. A recommended default is to compute facets from the current text query and base eligibility constraints, while excluding the facet's own selected filter when calculating its available alternatives. This allows a selected colour or category filter to show other available choices.

Facet calculations must avoid N+1 queries and excessive database aggregation.

### 10.2 Related results

When exact matches are absent or too few, return useful alternatives rather than unrelated products.

Possible fallback strategies:

1. Expand to approved synonyms.
2. Relax weak text matching while preserving explicit filters.
3. Find products in the same category.
4. Find products matching the same occasion, colour, or flavour.
5. Suggest relevant categories when product matches remain unavailable.

Explicit price bounds, publication rules, and availability constraints must not be silently discarded to generate alternatives.

If no relevant products exist, return an empty product list and useful category suggestions if available.

The response must distinguish exact query results from fallback recommendations, for example through a `match_type` field.

Do not use an arbitrary similarity threshold without evaluating it against the actual catalogue.

---

## 11. Recommended application structure

The following is the proposed logical layout. It may be simplified to fit the existing repository.

```text
backend/
└── apps/
    └── search/
        ├── __init__.py
        ├── apps.py
        ├── admin.py
        ├── urls.py
        ├── views.py
        ├── serializers.py
        ├── filters.py
        ├── pagination.py
        ├── selectors.py
        ├── services/
        │   ├── __init__.py
        │   ├── normalization.py
        │   ├── synonyms.py
        │   ├── query_parser.py
        │   ├── query_builder.py
        │   ├── ranking.py
        │   ├── facets.py
        │   ├── related_results.py
        │   └── search_service.py
        └── tests/
            ├── __init__.py
            ├── test_normalization.py
            ├── test_query_parser.py
            ├── test_synonyms.py
            ├── test_filters.py
            ├── test_ranking.py
            ├── test_facets.py
            ├── test_related_results.py
            ├── test_api.py
            └── test_performance.py
```

This is a proposal, not a claim that these files already exist. Do not create empty modules solely to match the diagram.

### 11.1 Module responsibilities

- `views.py`: thin HTTP layer.
- `serializers.py`: query parameter validation and response serialization.
- `filters.py`: validation and application of structured filters.
- `pagination.py`: search pagination if not handled by the project's common utilities.
- `selectors.py`: catalogue query access and reusable queryset helpers.
- `services/normalization.py`: query cleanup.
- `services/synonyms.py`: controlled synonym mappings.
- `services/query_parser.py`: supported structured intent extraction.
- `services/query_builder.py`: candidate queryset construction.
- `services/ranking.py`: relevance expressions and ordering.
- `services/facets.py`: facet aggregation.
- `services/related_results.py`: controlled fallback retrieval.
- `services/search_service.py`: coordinates the pipeline.

Avoid adding a dedicated model or search-index table until a concrete performance or functionality requirement justifies it.

---

## 12. API-independent service contract

The search service should be usable from a REST API today and potentially from other internal callers later.

Illustrative interface:

```python
search_products(
    query="pink birthday cake",
    filters={
        "product_type": "cake",
        "max_price": "1500",
    },
    sort="relevance",
    page=1,
    page_size=20,
)
```

The final implementation must define typed input and output structures consistent with the project's Python and Django conventions.

The service should return a structured result containing:

- Ranked product results.
- Pagination metadata.
- Applied filters.
- Facets when requested.
- Whether fallback results were used.
- Optional related category suggestions.

The service must not depend on `request`, `HttpRequest`, or DRF serializer objects internally. The HTTP layer validates request parameters and passes normalized inputs to the service.

---

## 13. Data and indexing strategy

### 13.1 No duplicated catalogue data

The catalogue is the authoritative data source.

Do not copy all product records into a separate search model for the initial implementation.

Search should build querysets against catalogue models and use annotations or database expressions to calculate relevance.

### 13.2 Full-text search

PostgreSQL full-text search may use a combined searchable document built from relevant catalogue fields.

A logical weighting strategy could prioritize:

- Product name: highest weight.
- Category and product type: high weight.
- Structured attributes: strong boosts where explicitly requested.
- Short description: medium weight.
- Full description: lower weight.

The exact vector construction must reflect the actual catalogue schema. Do not assume every listed field exists.

Where supported by the installed PostgreSQL and Django versions, use GIN indexes for full-text search vectors when query volume and performance justify them.

### 13.3 Substring and typo matching

Substring and typo matching may be valuable for product names and accessories.

PostgreSQL's `pg_trgm` extension is an option for similarity matching. Before relying on it:

- Verify that the target PostgreSQL environment supports it.
- Confirm permission to enable the extension.
- Confirm compatibility with the current Supabase setup.
- Add the required index and migration only after approval.
- Test similarity thresholds against real product names and queries.

Do not add expensive similarity operations to every field or every query without performance evaluation.

### 13.4 Attribute indexes

Frequently filtered catalogue fields should be indexed in their owning catalogue models where justified.

Examples include category, publication state, product type, and normalized attribute relationships.

Indexes must be designed after inspecting the actual model definitions and query plans. Avoid redundant indexes and speculative schema changes.

### 13.5 Query performance

Performance measures should include:

- Pagination with a bounded maximum page size.
- Avoiding N+1 queries through appropriate `select_related` and `prefetch_related`.
- Fetching only fields needed for ranking and serialization.
- Avoiding per-product database queries for facet counts.
- Using deterministic sorting.
- Inspecting SQL query plans for representative queries.
- Measuring query latency and database load before adding more infrastructure.

The service must not load the entire catalogue into Python for every search.

---

## 14. Search API design

The exact API contract will be documented separately in `search_api.md`. The structure document defines the expected endpoint behavior at a high level.

Recommended primary endpoint:

`GET /api/v1/search/`

Example request:

`GET /api/v1/search/?q=pink%20birthday%20cake&product_type=cake&max_price=1500&page=1&page_size=20`

The response should contain:

- `query`: normalized or display-safe query.
- `results`: ranked catalogue products.
- `count`: total matching count, if supported by the pagination strategy.
- `page` and `page_size`, or the project's standard pagination metadata.
- `facets`: available filter values and counts.
- `applied_filters`: validated filters.
- `fallback_used`: whether related-result fallback was applied.
- `suggestions`: optional related category or query suggestions.

Each product result should use the catalogue's canonical product identifier and include the minimum information needed for a search result card:

- Product identifier.
- Name.
- Slug or canonical detail identifier.
- Product type.
- Category summary where available.
- Primary image URL or equivalent catalogue-owned image representation.
- Display price or starting price, with clear semantics.
- Currency.
- Availability state appropriate for public display.
- Relevant matching metadata only when useful.

Do not duplicate all catalogue fields in the search response. Product detail pages remain responsible for full product information.

### 14.1 Optional autocomplete

Autocomplete is not required for the initial implementation.

If later required, add a separate lightweight endpoint that returns a small number of suggestions and avoids expensive full facet aggregation.

Potential endpoint:

`GET /api/v1/search/suggestions/?q=birt`

It should return only published, eligible catalogue products and approved category suggestions. Do not implement it unless the frontend requires live suggestions.

### 14.2 Error behavior

Use the project's standard validation error format for invalid parameters.

Reject or normalize invalid values consistently, including:

- Negative prices.
- `min_price` greater than `max_price`.
- Unsupported sort options.
- Invalid product-type values.
- Invalid pagination values.
- Excessively long queries.

An empty query may return a defined default listing if the storefront requires it, but it should not trigger an unbounded catalogue scan. The exact empty-query behavior must be aligned with the frontend's browse experience.

---

## 15. Security and privacy

Search is a public product-discovery feature, but its query handling still requires controls.

Requirements:

- Return only published products that are eligible for public discovery.
- Never expose draft or archived products to anonymous users.
- Never expose internal cost prices, supplier information, staff notes, or unpublished catalogue fields.
- Validate query length and all filter parameters.
- Use Django ORM expressions and parameterized query construction.
- Never interpolate raw user input into SQL.
- Allowlist sort fields and filter names.
- Bound pagination and expensive query operations.
- Apply rate limits if query volume or abuse requires them.
- Avoid logging sensitive query context unnecessarily.
- Do not log authentication tokens or personal information.
- Prevent query parameters from exposing private or customer-specific catalogue data.
- Treat product descriptions and metadata as data, not executable code.

Search must not bypass product visibility, current price checks, cart validation, or checkout rules.

---

## 16. Observability and analytics

Minimal operational observability should support troubleshooting without creating an unnecessary analytics platform.

Potential metrics:

- Search request count.
- Search latency.
- Empty-result rate.
- Query error rate.
- Facet computation latency.
- Database query count for representative requests.
- Frequency of fallback-result use.

Search-query analytics should be introduced only with an explicit data-retention and privacy policy. Avoid storing raw customer search history indefinitely by default.

If search analytics are added later, aggregate data where possible and separate operational metrics from customer-identifiable history.

---

## 17. Testing requirements

All tests should run against controlled test data and must not modify production catalogue records.

### 17.1 Query normalization

Test:

- Leading and trailing whitespace.
- Repeated spaces.
- Case normalization.
- Punctuation handling.
- Empty queries.
- Maximum query length.
- Preservation of meaningful numbers and terms.

### 17.2 Synonyms and intent parsing

Test representative queries:

- `bday cake`.
- `birthday cake`.
- `anniv cake`.
- `birthday candles`.
- `pink birthday cake`.
- `chocolate cake under 1500`.
- `cake between 1000 and 2000`.
- Unknown terms that should remain searchable.

Verify that synonyms do not silently impose incorrect filters.

### 17.3 Ranking

Test that:

- Exact product-name matches rank above incidental description matches.
- Explicit colour and occasion matches receive appropriate boosts.
- `birthday candles` prioritizes matching accessories.
- `birthday cake` prioritizes relevant cake products.
- Description-only matches remain possible.
- Price and availability filters do not get bypassed by relevance scoring.
- Sorting is deterministic.

### 17.4 Filters and facets

Test:

- Category filtering.
- Product-type filtering.
- Colour, occasion, and flavour filtering.
- Price boundaries.
- Availability filtering.
- Invalid values.
- Facet counts and selected-filter behavior.
- Published-product restrictions.

### 17.5 Related results

Test:

- Exact matches take priority.
- Synonym expansion can find relevant alternatives.
- Category suggestions appear when appropriate.
- Explicit price bounds are preserved.
- Unavailable and unpublished products are excluded.
- Completely unrelated products are not returned as fallback results.

### 17.6 API and security

Test:

- Anonymous search works where intended.
- Invalid parameters return the standard error format.
- Pagination limits are enforced.
- Draft and archived products remain hidden.
- Raw query input cannot alter SQL structure.
- Response fields do not leak internal catalogue data.
- Product and image URLs follow the catalogue's canonical serialization rules.

### 17.7 Performance

Use representative catalogue volumes and query patterns to measure:

- Database query count.
- Search latency.
- Facet aggregation cost.
- Similarity-search cost, if enabled.
- Pagination stability.

Do not assume acceptable performance based only on small unit-test fixtures.

---

## 18. Implementation sequence

Recommended development order:

1. Inspect existing catalogue models, serializers, query helpers, product types, categories, and availability rules.
2. Identify which searchable attributes already exist and which require catalogue work.
3. Define the internal search service input and output contract.
4. Implement normalization and a controlled synonym dictionary.
5. Implement structured filters using the existing catalogue schema.
6. Add PostgreSQL full-text matching and initial relevance ranking.
7. Add description matching and selected partial-match behavior.
8. Implement the unified cakes-and-accessories result format.
9. Add pagination and deterministic sorting.
10. Implement facets with appropriate query semantics.
11. Add related-result fallback behavior.
12. Optimize indexes and query plans based on actual performance.
13. Add automated ranking, filter, security, and performance tests.
14. Document the public API in `search_api.md`.
15. Verify the frontend integration using representative real catalogue data.
16. Evaluate ranking quality and tune weights before production release.

Do not introduce schema changes until the actual catalogue model has been inspected and the required changes approved.

---

## 19. Explicitly undecided items

| Item | Current status |
|---|---|
| Existing structured colour, occasion, and flavour fields | Must be verified against catalogue models |
| Product-type field and canonical values | Must match catalogue schema |
| Price filtering across variable-price variants | Exact aggregation policy pending |
| Combined-colour semantics | Recommended all-colours match when confidently parsed |
| Exact relevance weights | Must be tuned against real catalogue data |
| Typo tolerance | `pg_trgm` is optional pending extension and performance verification |
| Empty-query behavior | Must align with storefront browse requirements |
| Facet semantics | Recommended self-excluding facet counts |
| Related-result threshold | Must be evaluated against catalogue quality |
| Popularity ranking | Not required unless reliable data exists |
| Autocomplete | Optional; not required for launch |
| Search analytics retention | Not defined |
| External search engine | Not required unless PostgreSQL performance proves insufficient |

---

## 20. Acceptance criteria

The search app is ready for launch when:

- Customers can search cakes and accessories through one endpoint.
- Product names, categories, descriptions, and configured attributes participate in matching.
- Exact and strong matches rank above incidental matches.
- Colour, occasion, flavour, product type, price, and availability filters work against authoritative catalogue data.
- Published-product visibility is enforced for all queries and fallback results.
- Search results include useful product-card information without duplicating the entire catalogue model.
- Facets accurately reflect the documented filter semantics.
- Related results remain relevant and respect explicit constraints.
- Search performance has been measured using representative catalogue data.
- Tests cover ranking, normalization, filters, facets, security, and query performance.
- Cart and checkout independently revalidate price, variant, availability, and customization.
- The implementation does not require Elasticsearch or a separate search database for launch.

---

## 21. Non-goals for launch

Unless separately approved, do not implement:

- Elasticsearch or OpenSearch.
- A vector database or embedding-based semantic search.
- Personalized recommendation models.
- Machine-learning ranking.
- A separate search-index database.
- A full search analytics platform.
- Automatic product-attribute inference that silently rewrites catalogue data.
- A campaign or promotion engine.
- Search-driven cart or checkout operations.
- A mandatory autocomplete endpoint.

These may be evaluated later if actual search quality or database performance demonstrates a need.

---

**Final architectural rule:** `catalog` owns the products and their attributes; `search` interprets queries and ranks catalogue records. PostgreSQL supplies the initial search infrastructure, and the cart and checkout workflows remain responsible for confirming that a selected product can actually be purchased.