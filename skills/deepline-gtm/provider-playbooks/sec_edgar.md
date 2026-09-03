# SEC EDGAR guidance

Use SEC EDGAR for authoritative public-company filings and facts reported in those filings.

1. Resolve an exact ticker with `sec_edgar_resolve_company` when the CIK is unknown.
2. Use `sec_edgar_list_filings` to find the accession and primary document. Filter to forms such as `10-K`, `10-Q`, and earnings-related `8-K` filings when appropriate.
3. Use `sec_edgar_get_filing_index` before document retrieval so the exact primary document or exhibit name is known.
4. Use `sec_edgar_get_filing_document` with a bounded `max_chars`. Follow its `source_url` when the result is truncated.
5. Use `sec_edgar_get_company_concept` for one exact XBRL taxonomy tag. Preserve the returned unit, period, form, accession, and filing URL when citing a value.

Structured results are available at `toolResponse.raw`; company-concept facts are under `toolResponse.raw.units[].facts[]`. Type-check each `value`, and select a fact by unit, form, dates or SEC frame, and accession rather than assuming the first fact is the desired standalone quarter. Use filing documents for narrative text, not as the default source for a fact already present in XBRL JSON.

SEC facts are disclosures, not a canonical normalized financial statement. Company-specific extension tags, fiscal calendars, duplicate contexts, and restatements require interpretation. SEC EDGAR does not provide stock prices, analyst estimates, earnings calendars, or transcript feeds.
