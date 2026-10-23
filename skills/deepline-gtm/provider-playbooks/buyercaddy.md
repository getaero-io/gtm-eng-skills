# BuyerCaddy

Technographics: which software a company runs, and which companies run a given product.
Search products by search text or categoryId (list categories for IDs), then pass the product ID to company search or check installs by companyDomain.
buyercaddy_search_companies is the reverse lookup: filter.productIdIn or filter.vendorDomainIn returns companies that use the product (add countryIn, industryIn, employeeRangeIn, revenueRangeIn to narrow). page is 0-based. Use productIdInAnd true to require all listed products.
buyercaddy_find_customers_of_products takes a plain-language prompt and returns AI-compiled customers with a probability and a usage note, without domains. Treat it as leads to verify, not as confirmed installs.
Use companyDomain for installed-technology and competitor lookups, vendorDomain for vendor products.
File export is not available on any endpoint; page through results.
Billed per row returned; use small `size` values to cap spend. buyercaddy_find_customers_of_products ignores `size` and returns about 10 rows per call, so `size` does not cap its spend. The category list is free.
