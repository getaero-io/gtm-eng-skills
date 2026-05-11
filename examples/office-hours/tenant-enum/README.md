# Tenant Enumeration — Find Confirmed Customers of Any SaaS Product

Find every confirmed customer of 17 SaaS platforms by enumerating tenant subdomains and HTTP-probing platform fingerprints.

**Blog post:** [deepline.com/blog/find-every-customer-saas-tenant-enumeration](https://deepline.com/blog/find-every-customer-saas-tenant-enumeration)

## How it works

1. `subfinder` queries 46+ passive DNS/CT sources to enumerate all subdomains of the target platform (e.g. `jamfcloud.com`)
2. Filter to direct tenant slugs — strip nested subdomains, internal infra
3. `httpx -fr` fires 100 concurrent HEAD requests and returns those matching the platform's HTTP fingerprint
4. For wildcard platforms (Jamf), a secondary check verifies the final URL contains the expected path fragment
5. Output: CSV of confirmed tenant login URLs

**Live result (2026-05-07):** `jamfcloud.com` → 11,913 subdomains → 2,893 slug candidates → 1,357 HTTP 200 → **436 confirmed tenants**

## Requirements

```bash
# Primary path (recommended)
brew install subfinder httpx

# Fallback (no install needed, but crt.sh has frequent outages)
# pip install psycopg2-binary  # optional postgres fallback
```

## Usage

```bash
# List supported platforms
python3 ct_harvest.py --list

# Harvest a single platform
python3 ct_harvest.py --platform jamf --output jamf_tenants.csv

# Multiple platforms
python3 ct_harvest.py --platform zendesk salesforce atlassian --output results.csv

# All platforms
python3 ct_harvest.py --platform all --output all_tenants.csv

# Probe a known company list
python3 slug_probe.py --csv companies.csv --platforms probeable --output confirmed.csv

# Single company test
python3 slug_probe.py --domain shopify.com --company "Shopify" \
    --platforms zendesk salesforce atlassian
```

## Output columns

**ct_harvest.py** (bulk subdomain harvest):

| Column | Description |
|--------|-------------|
| `platform` | Platform label (e.g. "Jamf Cloud") |
| `slug` | Tenant slug (e.g. `github`) |
| `subdomain` | Full subdomain (e.g. `github.jamfcloud.com`) |
| `login_url` | Clickable login URL |
| `confirmed` | `yes` = HTTP probe confirmed / `crtsh_unprobed` = from CT logs, not HTTP-verified |
| `source` | `subfinder`, `crtsh_json`, or `crtsh_postgres` |

**slug_probe.py** (per-company probe from a domain/CSV list):

| Column | Description |
|--------|-------------|
| `domain` | Input company domain |
| `company_name` | Input company name |
| `platform` | Platform probed |
| `slug_tried` | First slug that returned a confirmed response |
| `login_url` | Clickable login URL (empty if no match) |
| `confirmed` | `yes` = confirmed live / `no` = no match / `crt_only` = needs ct_harvest.py |
| `probe_method` | How the check worked (e.g. `http_200`, `http_fragment`) |
| `all_slugs_tried` | All slug candidates tried, comma-separated |

## Platform fingerprints

| Platform | URL pattern | Live signal | Ghost signal |
|----------|-------------|-------------|--------------|
| Salesforce | `{slug}.my.salesforce.com` | HTTP 200 | HTTP 404 |
| Zendesk | `{slug}.zendesk.com` | HTTP 200 | HTTP 403 |
| Freshdesk | `{slug}.freshdesk.com` | HTTP 302 | HTTP 404 |
| Jamf Cloud | `{slug}.jamfcloud.com` | Final URL has `/view/sso/login` | Bare URL |
| Atlassian | `{slug}.atlassian.net` | HTTP 200 | HTTP 404 |
| ServiceNow | `{slug}.service-now.com` | HTTP 200 | Timeout |
| Salesloft | `{slug}.salesloft.com` | HTTP 200 | DNS NXDOMAIN |
| PagerDuty | `{slug}.pagerduty.com` | HTTP 405 | 0/timeout |
| Greenhouse | `job-boards.greenhouse.io/{slug}` | HTTP 200 | HTTP 404 |
| Workday | `{slug}.myworkday.com` | CT logs only | wildcard DNS |
| BambooHR | `{slug}.bamboohr.com` | CT logs only | wildcard DNS |
| Outreach | `{slug}.outreach.io` | CT logs only | wildcard DNS |
| Gong | `{slug}.app.gong.io` | CT logs only | wildcard DNS |
| Monday.com | `{slug}.monday.com` | CT logs only | wildcard DNS |
| HubSpot | `{slug}.hs-sites.com` | CT logs only | wildcard DNS |
| NetSuite | `{slug}.app.netsuite.com` | CT logs only | wildcard DNS |
| Datadog | `{slug}.datadoghq.com` | CT logs only | wildcard DNS |

CT-log-only platforms use wildcard DNS — every slug resolves regardless of whether a tenant exists. Use `ct_harvest.py` (subfinder path) for these; HTTP probing alone is unreliable.

> **Note on `-fr` flag:** `httpx` must be called with `-fr` (follow redirects). Without it, platforms that 302 before reaching 200 (Jamf, Salesforce, Freshdesk) are silently dropped.

## Slug generation

The tenant slug is almost always the domain prefix. `shopify.com` → `shopify`. The script generates up to 5 candidates in priority order:

1. Domain prefix with legal suffixes stripped (`tranetechnologies.com` → `trane`)
2. Company name hyphenated
3. Company name no-separator
4. Acronym (3+ word companies: `tcs` from Tata Consultancy Services)

## No API keys required

- `subfinder` and `httpx` are open source, free, install via Homebrew
- `crt.sh` is a public service, no auth
- The only cost is the Bloomberry seed list if you want to start from a known company list (~$0.21/result via [Deepline](https://deepline.com))
