# BuyerCaddy

Technographics: which software a company runs, and which companies run a given product.
Search products by search text or categoryId (list categories for IDs), then pass the product ID to company search or check installs by companyDomain.
buyercaddy_search_companies is the reverse lookup: filter.productIdIn or filter.vendorDomainIn returns companies that use the product (add countryIn, industryIn, employeeRangeIn, revenueRangeIn to narrow). page is 0-based: the first page is 0, and page 1 of a search with fewer matches than size is empty. Use productIdInAnd or vendorDomainInAnd true to require all listed products or vendors.
employeeRangeIn takes fixed bands, and "1,000 - 4,999" crosses common limits such as 2,000. When the task gives an exact headcount range, confirm headcount with a source that returns a number before counting a company in that band as a match.
For each company you list, cite its own detection. A company search with one productIdIn value fills hitsCount, dateFirstVerified and dateLastVerified on each row; cite those. A search with several products or with vendorDomainIn leaves them empty, so check each company you list with buyercaddy_check_products_in_use (companyDomain plus the productIds from buyercaddy_search_products) and cite productName, hitCount and dateLastVerified for each product. Pass productIds rather than productNames: a name such as "Salesforce" can report productInUse false for a company whose Sales Cloud install is listed as "Agentforce Sales (formerly Salesforce Sales Cloud)".
industryIn takes BuyerCaddy's own labels, such as "Software Development & Technical Consulting"; a general word such as "Software" matches few companies. Leave it out and check industry in the results when you do not know the label.
buyercaddy_find_customers_of_products takes a plain-language prompt and returns AI-compiled customers with a probability and a usage note, without domains or headcount. Treat it as leads to verify, not as confirmed installs or sizes.
Use companyDomain for installed-technology and competitor lookups, vendorDomain for vendor products.
File export is not available on any endpoint; page through results.
Billed per call, including calls that return no rows; `size` does not change the price, so request the rows you need in one call. buyercaddy_find_customers_of_products ignores `size` and returns about 10 rows.
