## Provider search filters reference

All providers support structured filters. This section is auto-generated from provider input schemas.

### Apollo People Search (preview)

`apollo_search_people`

Apollo people API search input.

  - `page` (number, optional) — Page number (1-500).
  - `per_page` (number, optional) — Results per page (1-100).
  - `person_titles` (string[], optional) — Job titles to match.
  - `include_similar_titles` (boolean, optional) — Include similar titles for person_titles matches.
  - `person_seniorities` (("owner" | "founder" | "c_suite" | "partner" | "vp" | "head" | "director" | "manager" | "senior" | "entry" | "intern")[], optional) — Seniority filter values defined by Apollo.
  - `person_locations` (string[], optional) — Person locations.
  - `organization_locations` (string[], optional) — Organization HQ locations.
  - `organization_num_employees_ranges` (string[], optional) — Employee ranges like '1,10', '11,50', '51,200'.
  - `q_organization_domains_list` (string[], optional) — Organization domains to include.
  - `contact_email_status` (string[], optional) — Email status values (e.g., 'verified', 'guessed').
  - `organization_ids` (string[], optional) — Apollo organization IDs to include.
  - `q_keywords` (string, optional) — Keyword query across person and organization fields.
  - `revenue_range.min` (number, optional) — Minimum numeric value.
  - `revenue_range.max` (number, optional) — Maximum numeric value.
  - `currently_using_any_of_technology_uids` (string[], optional) — Organizations using ANY of these technology UIDs.
  - `currently_using_all_of_technology_uids` (string[], optional) — Organizations using ALL of these technology UIDs.
  - `currently_not_using_any_of_technology_uids` (string[], optional) — Exclude organizations using ANY of these technology UIDs.
  - `q_organization_job_titles` (string[], optional) — Organizations hiring for these job titles.
  - `organization_job_locations` (string[], optional) — Organizations hiring in these locations.
  - `organization_num_jobs_range.min` (number, optional) — Minimum integer value.
  - `organization_num_jobs_range.max` (number, optional) — Maximum integer value.
  - `organization_job_posted_at_range.min` (string, optional) — Minimum date/time (ISO 8601).
  - `organization_job_posted_at_range.max` (string, optional) — Maximum date/time (ISO 8601).

### Apollo People Search (paid)

`apollo_people_search_paid`

Apollo people API search input.

  - `page` (number, optional) — Page number (1-500).
  - `per_page` (number, optional) — Results per page (1-100).
  - `person_titles` (string[], optional) — Job titles to match.
  - `include_similar_titles` (boolean, optional) — Include similar titles for person_titles matches.
  - `person_seniorities` (("owner" | "founder" | "c_suite" | "partner" | "vp" | "head" | "director" | "manager" | "senior" | "entry" | "intern")[], optional) — Seniority filter values defined by Apollo.
  - `person_locations` (string[], optional) — Person locations.
  - `organization_locations` (string[], optional) — Organization HQ locations.
  - `organization_num_employees_ranges` (string[], optional) — Employee ranges like '1,10', '11,50', '51,200'.
  - `q_organization_domains_list` (string[], optional) — Organization domains to include.
  - `contact_email_status` (string[], optional) — Email status values (e.g., 'verified', 'guessed').
  - `organization_ids` (string[], optional) — Apollo organization IDs to include.
  - `q_keywords` (string, optional) — Keyword query across person and organization fields.
  - `revenue_range.min` (number, optional) — Minimum numeric value.
  - `revenue_range.max` (number, optional) — Maximum numeric value.
  - `currently_using_any_of_technology_uids` (string[], optional) — Organizations using ANY of these technology UIDs.
  - `currently_using_all_of_technology_uids` (string[], optional) — Organizations using ALL of these technology UIDs.
  - `currently_not_using_any_of_technology_uids` (string[], optional) — Exclude organizations using ANY of these technology UIDs.
  - `q_organization_job_titles` (string[], optional) — Organizations hiring for these job titles.
  - `organization_job_locations` (string[], optional) — Organizations hiring in these locations.
  - `organization_num_jobs_range.min` (number, optional) — Minimum integer value.
  - `organization_num_jobs_range.max` (number, optional) — Maximum integer value.
  - `organization_job_posted_at_range.min` (string, optional) — Minimum date/time (ISO 8601).
  - `organization_job_posted_at_range.max` (string, optional) — Maximum date/time (ISO 8601).

### Apollo People Match

`apollo_people_match`

Apollo people match input. Supports id-based matching. `reveal_personal_emails` defaults to true.

  - `name` (string, optional) — Person's full name.
  - `email` (string, optional) — Person's email address.
  - `hashed_email` (string, optional) — Person's MD5-hashed email address.
  - `first_name` (string, optional) — Person's first name.
  - `last_name` (string, optional) — Person's last name.
  - `linkedin_url` (string, optional) — Person's LinkedIn profile URL.
  - `domain` (string, optional) — Company domain (e.g., 'apollo.io').
  - `organization_name` (string, optional) — Employer/company name.
  - `id` (string, optional) — Apollo person ID from a prior lookup. For best reliability, pair `id` with `first_name` (or email/linkedin_url).
  - `reveal_personal_emails` (boolean, optional) — When true, request personal email reveal (credit-consuming).

### Apollo Company Search

`apollo_company_search`

Apollo company API search input.

  - `page` (number, optional) — Page number (1-500).
  - `per_page` (number, optional) — Results per page (1-100).
  - `q_organization_domains_list` (string[], optional) — Organization domains to include.
  - `q_organization_name` (string, optional) — Organization name keyword search.
  - `organization_ids` (string[], optional) — Apollo organization IDs to include.
  - `organization_num_employees_ranges` (string[], optional) — Employee ranges like '1,10', '11,50', '51,200'.
  - `organization_locations` (string[], optional) — Organization HQ locations to include.
  - `organization_not_locations` (string[], optional) — Organization HQ locations to exclude.
  - `q_organization_keyword_tags` (string[], optional) — Organization keyword tags.
  - `revenue_range.min` (number, optional) — Minimum numeric value.
  - `revenue_range.max` (number, optional) — Maximum numeric value.
  - `currently_using_any_of_technology_uids` (string[], optional) — Organizations using ANY of these technology UIDs.
  - `latest_funding_amount_range.min` (number, optional) — Minimum numeric value.
  - `latest_funding_amount_range.max` (number, optional) — Maximum numeric value.
  - `total_funding_range.min` (number, optional) — Minimum numeric value.
  - `total_funding_range.max` (number, optional) — Maximum numeric value.
  - `latest_funding_date_range.min` (string, optional) — Minimum date/time (ISO 8601).
  - `latest_funding_date_range.max` (string, optional) — Maximum date/time (ISO 8601).
  - `q_organization_job_titles` (string[], optional) — Organizations hiring for these job titles.
  - `organization_job_locations` (string[], optional) — Organizations hiring in these locations.
  - `organization_num_jobs_range.min` (number, optional) — Minimum integer value.
  - `organization_num_jobs_range.max` (number, optional) — Maximum integer value.
  - `organization_job_posted_at_range.min` (string, optional) — Minimum date/time (ISO 8601).
  - `organization_job_posted_at_range.max` (string, optional) — Maximum date/time (ISO 8601).

### CrustData Company Search

`crustdata_companydb_search`

Searches CompanyDB using /screener/companydb/search with filters.

  - `filters` (array, **required**) — Array of filter conditions (AND-combined). Each: {filter_type, type, value} or {filter_name, type, value}. filter_name is syntactic sugar for filter_type (e.g. company_investors → crunchbase_investors, company_funding_stage → last_funding_round_type). Single object is accepted. Nested {op,conditions} groups supported for OR logic.
  - `filters[]` (object, **required**)
  - `filters[].filter_type` ("acquisition_status" | "company_name" | "company_type" | "company_website_domain" | "competitor_ids" | "competitor_websites" | "crunchbase_categories" | "crunchbase_investors" | "crunchbase_total_investment_usd" | "employee_count_range" | "employee_metrics.growth_12m" | "employee_metrics.growth_12m_percent" | "employee_metrics.growth_6m_percent" | "employee_metrics.latest_count" | "estimated_revenue_higher_bound_usd" | "estimated_revenue_lower_bound_usd" | "follower_metrics.growth_6m_percent" | "follower_metrics.latest_count" | "hq_country" | "hq_location" | "ipo_date" | "largest_headcount_country" | "last_funding_date" | "last_funding_round_type" | "linkedin_id" | "linkedin_industries" | "linkedin_profile_url" | "markets" | "region" | "tracxn_investors" | "year_founded", optional) — Field to filter on. Accepts filter_name as alias. Key mappings: company_investors → crunchbase_investors, company_funding_stage → last_funding_round_type, funding stage/round → last_funding_round_type, headcount/size → employee_count_range or employee_metrics.latest_count, industry → linkedin_industries, location → hq_country (ISO alpha-3) or hq_location or region, revenue → estimated_revenue_lower_bound_usd / estimated_revenue_higher_bound_usd, funding amount → crunchbase_total_investment_usd, domain → company_website_domain.
  - `filters[].type` ("=" | "!=" | "in" | "not_in" | ">" | "<" | "=>" | "=<" | "(.)" | "[.]", optional) — Operator: =, !=, in, not_in, >, <, =>, =<, (.) fuzzy contains, [.] substring.
  - `filters[].value` (string | number | boolean | (string | number | boolean)[], optional) — Filter value. When unsure of exact values for a field, call crustdata_companydb_autocomplete first (free, no credits): e.g. deepline tools execute crustdata_companydb_autocomplete --payload '{"field":"last_funding_round_type","query":"series","limit":10}' --json. hq_country uses ISO 3166-1 alpha-3 codes (USA, GBR, CAN).
  - `filters[].value[]` (string | number | boolean, optional)
  - `filters[].op` ("and" | "or", optional) — Logical operator for conditions.
  - `filters[].conditions` (array, optional) — Nested filter conditions.
  - `filters[].conditions[]` (object, optional)
  - `filters[].conditions[].filter_type` ("acquisition_status" | "company_name" | "company_type" | "company_website_domain" | "competitor_ids" | "competitor_websites" | "crunchbase_categories" | "crunchbase_investors" | "crunchbase_total_investment_usd" | "employee_count_range" | "employee_metrics.growth_12m" | "employee_metrics.growth_12m_percent" | "employee_metrics.growth_6m_percent" | "employee_metrics.latest_count" | "estimated_revenue_higher_bound_usd" | "estimated_revenue_lower_bound_usd" | "follower_metrics.growth_6m_percent" | "follower_metrics.latest_count" | "hq_country" | "hq_location" | "ipo_date" | "largest_headcount_country" | "last_funding_date" | "last_funding_round_type" | "linkedin_id" | "linkedin_industries" | "linkedin_profile_url" | "markets" | "region" | "tracxn_investors" | "year_founded", optional) — Field to filter on. Accepts filter_name as alias. Key mappings: company_investors → crunchbase_investors, company_funding_stage → last_funding_round_type, funding stage/round → last_funding_round_type, headcount/size → employee_count_range or employee_metrics.latest_count, industry → linkedin_industries, location → hq_country (ISO alpha-3) or hq_location or region, revenue → estimated_revenue_lower_bound_usd / estimated_revenue_higher_bound_usd, funding amount → crunchbase_total_investment_usd, domain → company_website_domain.
  - `filters[].conditions[].type` ("=" | "!=" | "in" | "not_in" | ">" | "<" | "=>" | "=<" | "(.)" | "[.]", optional) — Operator: =, !=, in, not_in, >, <, =>, =<, (.) fuzzy contains, [.] substring.
  - `filters[].conditions[].value` (string | number | boolean | (string | number | boolean)[], optional) — Filter value. When unsure of exact values for a field, call crustdata_companydb_autocomplete first (free, no credits): e.g. deepline tools execute crustdata_companydb_autocomplete --payload '{"field":"last_funding_round_type","query":"series","limit":10}' --json. hq_country uses ISO 3166-1 alpha-3 codes (USA, GBR, CAN).
  - `filters[].conditions[].op` ("and" | "or", optional) — Logical operator for conditions.
  - `filters[].conditions[].conditions` (array, optional) — Nested filter conditions.
  - `limit` (number, optional)
  - `cursor` (string, optional) — Pagination cursor.
  - `sorts` (array, optional) — Sort criteria array.
  - `sorts[].column` (string, optional) — Field to sort by (e.g. employee_metrics.latest_count).
  - `sorts[].order` ("asc" | "desc", optional) — Sort order: asc or desc.

### CrustData Person Search

`crustdata_persondb_search`

Searches PersonDB using /screener/persondb/search with filters.

  - `filters` (array, **required**) — Array of filter conditions (AND-combined). Each: {filter_type, type, value} or {filter_name, type, value}. filter_name is syntactic sugar for filter_type. Single object is accepted. Nested {op,conditions} groups supported for OR logic.
  - `filters[]` (object, **required**)
  - `filters[].filter_type` ("current_employers.company_website_domain" | "current_employers.seniority_level" | "current_employers.title" | "headline" | "num_of_connections" | "region" | "years_of_experience_raw", optional) — Field to filter on. Key mappings: job title → current_employers.title, seniority → current_employers.seniority_level, company/employer → current_employers.company_website_domain, location → region, experience → years_of_experience_raw, bio/summary → headline, connections → num_of_connections.
  - `filters[].type` ("=" | "!=" | "in" | "not_in" | ">" | "<" | "=>" | "=<" | "(.)" | "[.]" | "geo_distance", optional) — Operator: =, !=, in, not_in, >, <, =>, =<, (.) fuzzy contains, [.] substring, geo_distance (region only).
  - `filters[].value` (string | number | boolean | (string | number | boolean)[] | object, optional) — Filter value (or geo_distance object for region). When unsure of exact values for a field, call crustdata_persondb_autocomplete first (free, no credits): e.g. deepline tools execute crustdata_persondb_autocomplete --payload '{"field":"current_employers.title","query":"engineer","limit":10}' --json.
  - `filters[].value[]` (string | number | boolean, optional)
  - `filters[].value.location` (string, optional)
  - `filters[].value.distance` (number, optional)
  - `filters[].value.unit` ("km" | "mi" | "miles" | "m" | "meters" | "ft" | "feet", optional)
  - `filters[].op` ("and" | "or", optional) — Logical operator for conditions.
  - `filters[].conditions` (array, optional) — Nested filter conditions.
  - `filters[].conditions[]` (object, optional)
  - `filters[].conditions[].filter_type` ("current_employers.company_website_domain" | "current_employers.seniority_level" | "current_employers.title" | "headline" | "num_of_connections" | "region" | "years_of_experience_raw", optional) — Field to filter on. Key mappings: job title → current_employers.title, seniority → current_employers.seniority_level, company/employer → current_employers.company_website_domain, location → region, experience → years_of_experience_raw, bio/summary → headline, connections → num_of_connections.
  - `filters[].conditions[].type` ("=" | "!=" | "in" | "not_in" | ">" | "<" | "=>" | "=<" | "(.)" | "[.]" | "geo_distance", optional) — Operator: =, !=, in, not_in, >, <, =>, =<, (.) fuzzy contains, [.] substring, geo_distance (region only).
  - `filters[].conditions[].value` (string | number | boolean | (string | number | boolean)[] | object, optional) — Filter value (or geo_distance object for region). When unsure of exact values for a field, call crustdata_persondb_autocomplete first (free, no credits): e.g. deepline tools execute crustdata_persondb_autocomplete --payload '{"field":"current_employers.title","query":"engineer","limit":10}' --json.
  - `filters[].conditions[].op` ("and" | "or", optional) — Logical operator for conditions.
  - `filters[].conditions[].conditions` (array, optional) — Nested filter conditions.
  - `limit` (number, optional)
  - `cursor` (string, optional) — Pagination cursor.
  - `sorts` (array, optional) — Sort criteria array.
  - `sorts[].column` (string, optional) — Field to sort by (e.g. employee_metrics.latest_count).
  - `sorts[].order` ("asc" | "desc", optional) — Sort order: asc or desc.
  - `postProcessing.exclude_profiles` (string[], optional) — Exclude specific profile IDs.
  - `postProcessing.exclude_names` (string[], optional) — Exclude matching names.
  - `preview` (boolean, optional) — Enable preview mode.

### CrustData Company Autocomplete

`crustdata_companydb_autocomplete`

Fetches exact filter values using /screener/companydb/autocomplete. Free, no credits consumed.

  - `field` ("acquisition_status" | "company_name" | "company_type" | "company_website_domain" | "competitor_ids" | "competitor_websites" | "crunchbase_categories" | "crunchbase_investors" | "crunchbase_total_investment_usd" | "employee_count_range" | "employee_metrics.growth_12m" | "employee_metrics.growth_12m_percent" | "employee_metrics.growth_6m_percent" | "employee_metrics.latest_count" | "estimated_revenue_higher_bound_usd" | "estimated_revenue_lower_bound_usd" | "follower_metrics.growth_6m_percent" | "follower_metrics.latest_count" | "hq_country" | "hq_location" | "ipo_date" | "largest_headcount_country" | "last_funding_date" | "last_funding_round_type" | "linkedin_id" | "linkedin_industries" | "linkedin_profile_url" | "markets" | "region" | "tracxn_investors" | "year_founded", **required**) — Field name to autocomplete. Must be one of: acquisition_status, company_name, company_type, company_website_domain, competitor_ids, competitor_websites, crunchbase_categories, crunchbase_investors, crunchbase_total_investment_usd, employee_count_range, employee_metrics.growth_12m, employee_metrics.growth_12m_percent, employee_metrics.growth_6m_percent, employee_metrics.latest_count, estimated_revenue_higher_bound_usd, estimated_revenue_lower_bound_usd, follower_metrics.growth_6m_percent, follower_metrics.latest_count, hq_country, hq_location, ipo_date, largest_headcount_country, last_funding_date, last_funding_round_type, linkedin_id, linkedin_industries, linkedin_profile_url, markets, region, tracxn_investors, year_founded. Key mappings: funding stage/round → last_funding_round_type, headcount/size → employee_count_range, industry → linkedin_industries, location → hq_country (ISO alpha-3) or hq_location. Note: hq_country uses 3-letter ISO codes (USA, GBR, CAN), not country names.
  - `query` (string, **required**) — Partial text to match. For hq_country, use ISO code patterns (e.g. "US", "USA", "GBR") rather than country names.
  - `limit` (number, optional)

### CrustData Person Autocomplete

`crustdata_persondb_autocomplete`

Fetches exact filter values using /screener/persondb/autocomplete. Free, no credits consumed.

  - `field` ("current_employers.company_website_domain" | "current_employers.seniority_level" | "current_employers.title" | "headline" | "num_of_connections" | "region" | "years_of_experience_raw", **required**) — Field name to autocomplete. Must be one of: current_employers.company_website_domain, current_employers.seniority_level, current_employers.title, headline, num_of_connections, region, years_of_experience_raw. Key mappings: job title → current_employers.title, seniority → current_employers.seniority_level, location → region, company/employer → current_employers.company_website_domain, experience → years_of_experience_raw, bio/summary → headline.
  - `query` (string, **required**) — Partial text to match. Examples: "san franci" for region, "Eng" for job titles.
  - `limit` (number, optional)

### CrustData People Search

`crustdata_people_search`

Searches people at a company via PersonDB using derived filters.

  - `companyDomain` (string, **required**) — Company website domain to match.
  - `titleKeywords` (string | string[], **required**) — Title keyword(s) to match.
  - `profileKeywords` (string | string[], optional) — Profile headline keyword(s).
  - `country` (string, optional) — Country or region filter.
  - `seniority` (string | string[], optional) — Seniority level(s). Canonical values: CXO, Vice President, Director, Manager, Senior, Entry, Training, Owner, Partner, Unpaid. Common aliases (c-suite, vp, founder, junior, intern) are auto-normalized.
  - `fuzzyTitle` (boolean, optional) — Use fuzzy title matching (default true).
  - `limit` (number, optional)

### PDL Person Search

`peopledatalabs_person_search`

People Data Labs person search input.

  - `query` (record, optional) — Elasticsearch-style query. Use this OR `sql`, not both. If you are unsure about field names, prefer `sql` with known fields.
  - `sql` (string, optional) — SQL must be in the form `SELECT * FROM person WHERE ...`. Use single quotes for string literals (e.g., name='people data labs'). You must use valid PDL field names and nested subfields (e.g., `experience.title.name`, not `experience`). Column selection and LIMIT are ignored by PDL; always use `SELECT *`. Example: SELECT * FROM person WHERE location_country='mexico' AND job_title_role='health' AND phone_numbers IS NOT NULL.
  - `size` (number, optional) — Number of records to return (1-100).
  - `scroll_token` (string, optional) — Token for retrieving the next page of results.
  - `dataset` (string, optional) — Optional dataset selector supported by PDL.
  - `titlecase` (boolean, optional) — Normalize output text casing.
  - `data_include` (string, optional) — Avoid using data_include unless you want partial fields only.
  - `pretty` (boolean, optional) — Pretty-print response JSON.

### PDL Company Search

`peopledatalabs_company_search`

People Data Labs company search input.

  - `query` (record, optional) — Elasticsearch-style query. Use this OR `sql`, not both. If you are unsure about field names, prefer `sql` with known fields.
  - `sql` (string, optional) — SQL must be in the form `SELECT * FROM company WHERE ...`. Use single quotes for string literals. You must use valid PDL field names and nested subfields (e.g., `location.country`, not `location`). Column selection and LIMIT are ignored by PDL; always use `SELECT *`. Example: SELECT * FROM company WHERE location_country='mexico' AND phone IS NOT NULL.
  - `size` (number, optional) — Number of records to return (1-100).
  - `scroll_token` (string, optional) — Token for retrieving the next page of results.
  - `titlecase` (boolean, optional) — Normalize output text casing.
  - `data_include` (string, optional) — Avoid using data_include unless you want partial fields only.
  - `pretty` (boolean, optional) — Pretty-print response JSON.

### Exa Search

`exa_search`

Exa raw search input.

  - `query` (string, **required**) — The search query string.
  - `additionalQueries` (string[], optional) — Additional queries (used with type="deep" to expand coverage).
  - `type` ("auto" | "fast" | "deep" | "neural" | "instant", optional) — Search type (auto chooses the best strategy).
  - `category` ("company" | "people" | "news" | "research paper" | "tweet" | "personal site" | "financial report", optional) — Optional result category filter.
  - `numResults` (number, optional) — Number of results to return (max 100).
  - `includeDomains` (string[], optional) — Only include results from these domains.
  - `excludeDomains` (string[], optional) — Exclude results from these domains.
  - `startCrawlDate` (string, optional) — Only include links crawled after this ISO date-time.
  - `endCrawlDate` (string, optional) — Only include links crawled before this ISO date-time.
  - `startPublishedDate` (string, optional) — Only include links published after this ISO date-time.
  - `endPublishedDate` (string, optional) — Only include links published before this ISO date-time.
  - `includeText` (string[], optional) — Require these text snippets to appear in page content.
  - `excludeText` (string[], optional) — Exclude pages containing these text snippets.
  - `userLocation` (string, optional) — Two-letter ISO country code, e.g. "US".
  - `contents.text` (boolean | object, optional) — Text extraction settings.
  - `contents.text.maxCharacters` (number, optional) — Maximum characters for full page text (use to cap response size).
  - `contents.text.includeHtmlTags` (boolean, optional) — Include HTML tags in the returned text.
  - `contents.text.verbosity` ("compact" | "standard" | "full", optional) — Controls verbosity of extracted text.
  - `contents.text.includeSections` (("header" | "navigation" | "banner" | "body" | "sidebar" | "footer" | "metadata")[], optional) — Only include content from these sections.
  - `contents.text.excludeSections` (("header" | "navigation" | "banner" | "body" | "sidebar" | "footer" | "metadata")[], optional) — Exclude content from these sections.
  - `contents.highlights` (boolean | object, optional) — Highlight settings.
  - `contents.highlights.numSentences` (number, optional) — Number of sentences per highlight snippet.
  - `contents.highlights.highlightsPerUrl` (number, optional) — Number of highlight snippets per URL.
  - `contents.highlights.query` (string, optional) — Custom query to guide highlight selection.
  - `contents.highlights.maxCharacters` (number, optional) — Maximum characters returned for highlights.
  - `contents.summary.query` (string, optional) — Custom query for the summary.
  - `contents.summary.schema` (record, optional) — JSON Schema for structured summary output (validated).
  - `contents.livecrawl` ("never" | "fallback" | "preferred" | "always", optional) — Live crawl behavior (deprecated in Exa docs; prefer maxAgeHours).
  - `contents.livecrawlTimeout` (number, optional) — Live crawl timeout in milliseconds.
  - `contents.maxAgeHours` (number, optional) — Max age (hours) for cached content before live crawl.
  - `contents.subpages` (number, optional) — Number of subpages to crawl from each result.
  - `contents.subpageTarget` (string | string[], optional) — Subpage keyword(s) to target.
  - `contents.extras.links` (number, optional) — Number of links to return per result.
  - `contents.extras.imageLinks` (number, optional) — Number of image links to return per result.
  - `contents.context` (boolean | object, optional) — Combined context settings. Returns a single context string from all results.
  - `contents.context.maxCharacters` (number, optional) — Maximum characters for the combined context string. Exa recommends 10,000+ characters for best results.
  - `context` (boolean | object, optional)
  - `context.maxCharacters` (number, optional) — Maximum characters for the combined context string. Exa recommends 10,000+ characters for best results.
  - `moderation` (boolean, optional) — Enable content moderation (may reduce recall).

### Exa Company Search

`exa_company_search`

Exa company search input.

  - `query` (string, **required**)
  - `additionalQueries` (string[], optional) — Additional queries (used with type="deep" to expand coverage).
  - `type` ("auto" | "fast" | "deep" | "neural" | "instant", optional)
  - `numResults` (number, optional) — Number of results to return (max 100).
  - `includeDomains` (string[], optional)
  - `excludeDomains` (string[], optional) — Exclude results from these domains.
  - `userLocation` (string, optional) — Two-letter ISO country code, e.g. "US".
  - `contents.text` (boolean | object, optional) — Text extraction settings.
  - `contents.text.maxCharacters` (number, optional) — Maximum characters for full page text (use to cap response size).
  - `contents.text.includeHtmlTags` (boolean, optional) — Include HTML tags in the returned text.
  - `contents.text.verbosity` ("compact" | "standard" | "full", optional) — Controls verbosity of extracted text.
  - `contents.text.includeSections` (("header" | "navigation" | "banner" | "body" | "sidebar" | "footer" | "metadata")[], optional) — Only include content from these sections.
  - `contents.text.excludeSections` (("header" | "navigation" | "banner" | "body" | "sidebar" | "footer" | "metadata")[], optional) — Exclude content from these sections.
  - `contents.highlights` (boolean | object, optional) — Highlight settings.
  - `contents.highlights.numSentences` (number, optional) — Number of sentences per highlight snippet.
  - `contents.highlights.highlightsPerUrl` (number, optional) — Number of highlight snippets per URL.
  - `contents.highlights.query` (string, optional) — Custom query to guide highlight selection.
  - `contents.highlights.maxCharacters` (number, optional) — Maximum characters returned for highlights.
  - `contents.summary.query` (string, optional) — Custom query for the summary.
  - `contents.summary.schema` (record, optional) — JSON Schema for structured summary output (validated).
  - `contents.livecrawl` ("never" | "fallback" | "preferred" | "always", optional) — Live crawl behavior (deprecated in Exa docs; prefer maxAgeHours).
  - `contents.livecrawlTimeout` (number, optional) — Live crawl timeout in milliseconds.
  - `contents.maxAgeHours` (number, optional) — Max age (hours) for cached content before live crawl.
  - `contents.subpages` (number, optional) — Number of subpages to crawl from each result.
  - `contents.subpageTarget` (string | string[], optional) — Subpage keyword(s) to target.
  - `contents.extras.links` (number, optional) — Number of links to return per result.
  - `contents.extras.imageLinks` (number, optional) — Number of image links to return per result.
  - `contents.context` (boolean | object, optional) — Combined context settings. Returns a single context string from all results.
  - `contents.context.maxCharacters` (number, optional) — Maximum characters for the combined context string. Exa recommends 10,000+ characters for best results.
  - `context` (boolean | object, optional)
  - `context.maxCharacters` (number, optional) — Maximum characters for the combined context string. Exa recommends 10,000+ characters for best results.
  - `moderation` (boolean, optional) — Enable content moderation (may reduce recall).

### Exa People Search

`exa_people_search`

Exa people search input.

  - `query` (string, **required**)
  - `additionalQueries` (string[], optional) — Additional queries (used with type="deep" to expand coverage).
  - `type` ("auto" | "fast" | "deep" | "neural" | "instant", optional)
  - `numResults` (number, optional) — Number of results to return (max 100).
  - `includeDomains` (string[], optional)
  - `excludeDomains` (string[], optional) — Exclude results from these domains.
  - `userLocation` (string, optional) — Two-letter ISO country code, e.g. "US".
  - `contents.text` (boolean | object, optional) — Text extraction settings.
  - `contents.text.maxCharacters` (number, optional) — Maximum characters for full page text (use to cap response size).
  - `contents.text.includeHtmlTags` (boolean, optional) — Include HTML tags in the returned text.
  - `contents.text.verbosity` ("compact" | "standard" | "full", optional) — Controls verbosity of extracted text.
  - `contents.text.includeSections` (("header" | "navigation" | "banner" | "body" | "sidebar" | "footer" | "metadata")[], optional) — Only include content from these sections.
  - `contents.text.excludeSections` (("header" | "navigation" | "banner" | "body" | "sidebar" | "footer" | "metadata")[], optional) — Exclude content from these sections.
  - `contents.highlights` (boolean | object, optional) — Highlight settings.
  - `contents.highlights.numSentences` (number, optional) — Number of sentences per highlight snippet.
  - `contents.highlights.highlightsPerUrl` (number, optional) — Number of highlight snippets per URL.
  - `contents.highlights.query` (string, optional) — Custom query to guide highlight selection.
  - `contents.highlights.maxCharacters` (number, optional) — Maximum characters returned for highlights.
  - `contents.summary.query` (string, optional) — Custom query for the summary.
  - `contents.summary.schema` (record, optional) — JSON Schema for structured summary output (validated).
  - `contents.livecrawl` ("never" | "fallback" | "preferred" | "always", optional) — Live crawl behavior (deprecated in Exa docs; prefer maxAgeHours).
  - `contents.livecrawlTimeout` (number, optional) — Live crawl timeout in milliseconds.
  - `contents.maxAgeHours` (number, optional) — Max age (hours) for cached content before live crawl.
  - `contents.subpages` (number, optional) — Number of subpages to crawl from each result.
  - `contents.subpageTarget` (string | string[], optional) — Subpage keyword(s) to target.
  - `contents.extras.links` (number, optional) — Number of links to return per result.
  - `contents.extras.imageLinks` (number, optional) — Number of image links to return per result.
  - `contents.context` (boolean | object, optional) — Combined context settings. Returns a single context string from all results.
  - `contents.context.maxCharacters` (number, optional) — Maximum characters for the combined context string. Exa recommends 10,000+ characters for best results.
  - `context` (boolean | object, optional)
  - `context.maxCharacters` (number, optional) — Maximum characters for the combined context string. Exa recommends 10,000+ characters for best results.
  - `moderation` (boolean, optional) — Enable content moderation (may reduce recall).

### Exa Answer

`exa_answer`

Exa answer input.

  - `query` (string, **required**) — Question to answer using web results.
  - `stream` (boolean, optional) — Stream tokens as they are generated.
  - `text` (boolean, optional) — Include full source text in citations.
  - `outputSchema` (any, optional) — JSON Schema to return a structured answer. Supports arbitrary user-defined schema shape.

### Exa Research

`exa_research`

Exa research input.

  - `instructions` (string, **required**)
  - `model` ("exa-research-fast" | "exa-research", optional)
  - `outputSchema` (any, optional)

### Hunter People Find

`hunter_people_find`

Enrich one person by email or LinkedIn profile.

  - `email` (string, optional) — Work email for person enrichment lookup.
  - `linkedin` (string, optional) — LinkedIn profile URL or handle.

### Hunter Companies Find

`hunter_companies_find`

Enrich one company profile by domain.

  - `domain` (string, **required**) — Company domain to enrich.

### Hunter Combined Find

`hunter_combined_find`

Fetch person and company enrichment in one response envelope.

  - `email` (string, optional) — Email for combined person+company enrichment.
  - `linkedin` (string, optional) — LinkedIn profile URL/handle for person enrichment.
  - `domain` (string, optional) — Company domain when person identity is incomplete.

### Hunter Discover

`hunter_discover`

Discover companies matching ICP criteria. This call is free in Hunter.

  - `query` (string, optional) — Natural-language company search query. Prefer this for broad ICP discovery.
  - `organization.domain` (string[], optional)
  - `organization.name` (string[], optional)
  - `similar_to.domain` (string, optional)
  - `similar_to.name` (string, optional)
  - `headquarters_location.include` (array, optional)
  - `headquarters_location.include[].continent` (string, optional) — Continent name (for example Europe, North America).
  - `headquarters_location.include[].business_region` (string, optional) — Business region (AMER, EMEA, APAC, LATAM).
  - `headquarters_location.include[].country` (string, optional) — ISO 3166-1 alpha-2 country code (for example US).
  - `headquarters_location.include[].state` (string, optional) — US state code (for example CA). Requires country=US.
  - `headquarters_location.include[].city` (string, optional) — City name (for example San Francisco).
  - `headquarters_location.exclude` (array, optional)
  - `headquarters_location.exclude[].continent` (string, optional) — Continent name (for example Europe, North America).
  - `headquarters_location.exclude[].business_region` (string, optional) — Business region (AMER, EMEA, APAC, LATAM).
  - `headquarters_location.exclude[].country` (string, optional) — ISO 3166-1 alpha-2 country code (for example US).
  - `headquarters_location.exclude[].state` (string, optional) — US state code (for example CA). Requires country=US.
  - `headquarters_location.exclude[].city` (string, optional) — City name (for example San Francisco).
  - `industry.include` (string[], optional)
  - `industry.exclude` (string[], optional)
  - `headcount` (string[], optional) — Accepted values include 1-10, 11-50, 51-200, 201-500, 501-1000, 1001-5000, 5001-10000, 10001+.
  - `company_type.include` (string[], optional)
  - `company_type.exclude` (string[], optional)
  - `keywords.include` (string[], optional)
  - `keywords.exclude` (string[], optional)
  - `keywords.match` ("all" | "any", optional)
  - `technology.include` (string[], optional)
  - `technology.exclude` (string[], optional)
  - `technology.match` ("all" | "any", optional)
  - `limit` (number, optional) — Max domains returned (default 100). Changing this requires a Hunter Premium plan.
  - `offset` (number, optional) — Number of domains to skip for pagination. Non-zero offsets require a Hunter Premium plan.

### Hunter Domain Search

`hunter_domain_search`

Find email addresses for a specific company domain with confidence and sources.

  - `domain` (string, **required**) — Company domain to search (for example stripe.com).
  - `company` (string, optional) — Company name hint to improve matching.
  - `limit` (number, optional) — Max emails returned.
  - `offset` (number, optional) — Pagination offset.
  - `type` ("personal" | "generic", optional) — Return only personal emails or only role-based/generic emails.
  - `seniority` (string[], optional) — Filter by seniority labels.
  - `department` (string[], optional) — Filter by department labels.
  - `required_field` (string[], optional) — Require specific returned fields.

### Hunter Email Finder

`hunter_email_finder`

Find the most likely work email from name + domain.

  - `domain` (string, **required**) — Company domain (for example reddit.com).
  - `first_name` (string, **required**) — First name of the contact.
  - `last_name` (string, **required**) — Last name of the contact.
  - `full_name` (string, optional) — Optional full name alias for first + last.
  - `company` (string, optional) — Company name hint when multiple domains exist.
  - `max_duration` (number, optional) — Lookup timeout in seconds.

### LeadMagic Role Finder

`leadmagic_role_finder`

Find people by job title at a company.

  - `company_domain` (string, optional) — Company domain (e.g. acme.com).
  - `company_name` (string, optional) — Company name.
  - `job_title` (string, **required**) — Target job title (e.g. VP Sales).

### LeadMagic Company Search

`leadmagic_company_search`

Search for companies by attributes.

  - `company_domain` (string, optional) — Company domain to match.
  - `company_name` (string, optional) — Company name to match.
  - `profile_url` (string, optional) — LinkedIn/company profile URL.
  - `domain` (string, optional) — Legacy alias for company_domain.
  - `name` (string, optional) — Legacy alias for company_name.

### LeadMagic Profile Search

`leadmagic_profile_search`

Fetch a detailed professional profile by LinkedIn URL.

  - `profile_url` (string, **required**) — LinkedIn profile URL.

### LeadMagic Competitors Search

`leadmagic_competitors_search`

Find competitors for a company.

  - `company_domain` (string, **required**) — Company domain to analyze.

### LeadMagic B2B Ads Search

`leadmagic_b2b_ads_search`

Find B2B ads by company domain.

  - `company_domain` (string, optional) — Company domain to analyze.
  - `company_name` (string, optional) — Company name to analyze.
  - `domain` (string, optional) — Legacy alias for company_domain.

### Adyntel Facebook Ad Search

`adyntel_facebook_ad_search`

Meta keyword ad search across the ad library for advertiser and creative discovery.

  - `keyword` (string, **required**) — Keyword to search in Meta ad library.
  - `country_code` (string, optional) — Optional country filter code.

### Google Search

`google_search`

Run a Google Custom Search JSON API query. Best for broad B2B recall (contact, company, and domain discovery) before enrichment.

  - `query` (string, **required**) — Search query string. B2B patterns: contact LinkedIn (`site:linkedin.com/in "First Last" "Company"`), company LinkedIn (`site:linkedin.com/company "Company"`), email/domain validation (`"First Last" "company.com"`).
  - `cx` (string, optional) — Custom Search Engine ID. Defaults to GOOGLE_SEARCH_ENGINE_ID.
  - `num` (number, optional) — Results per page (1-10).
  - `start` (number, optional) — 1-indexed start result position.
  - `gl` (string, optional) — Country code (e.g. us).
  - `lr` (string, optional) — Language restrict (e.g. lang_en).
  - `dateRestrict` (string, optional) — Date restriction (e.g. d7, w2, m6).
  - `siteSearch` (string, optional) — Restrict results to a domain.
  - `siteSearchFilter` ("i" | "e", optional) — Include (i) or exclude (e) siteSearch domain.
  - `safe` ("off" | "active", optional) — SafeSearch mode.

### Parallel Search

`parallel_search`

Parallel search input. Requires objective or search_queries.

No documented fields.

