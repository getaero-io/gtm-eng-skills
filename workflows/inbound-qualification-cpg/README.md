# Inbound Qualification — CPG

A Deepline cloud workflow that qualifies inbound CPG / DTC brand signups end-to-end.

## What it does

Takes an inbound form submission (email + brand domain + revenue + form fields), then in a single 26-step pipeline:

1. **Validates** the email and filters junk submissions
2. **Detects retail-locator widget** by scraping the brand's `/store-locator` (or auto-discovered locator) page raw HTML
3. **Extracts retailer count + names** by hitting the widget's public JSON API directly via `generic_http_request` — supports Storepoint, Stockist, Closeby, Storerocket, Storemapper, Bullseye, and Brandify
4. **Falls back to firecrawl_extract** with structured AI for brands with no widget (custom HTML store lists)
5. **Enriches the company** via Deepline native + Crustdata waterfall
6. **Classifies CPG vs non-CPG** via Sonnet 4.6 with structured output
7. **Scores** the lead on CPG fit + revenue + title seniority + retail tier (0-14)
8. **Routes** to one of: create_deal / manual_review / partner_referral / non_cpg_decline / drop
9. **Drafts** a rep-ready Slack brief + outbound email + LinkedIn DM (only on create_deal)
10. **Posts** the brief to Slack with [Approve & Send] [Edit] [Skip] buttons

## Why this is interesting

Most retail-presence detection scrapes the homepage and asks an LLM to guess. This workflow goes one level deeper: it sniffs the widget's embed key from raw HTML, then calls the widget's own free public JSON API to get the *actual* retailer list. In testing this turned brands that previously showed 0 retailers into ones with 557 named locations (Storepoint) and 1,472 (Stockist).

## Cost

About $0.20-0.50 per inbound (mostly Sonnet for classify + brief + email; Firecrawl is $0.001-0.002 per scrape; locator API calls are free).

## Deploy

```bash
# 1. Edit workflow.json:
#    - Replace SLACK_CHANNELS map values with your real channel names
#    - Replace REPLACE_ME_REP_NAME with your sales rep's first name (used in email/DM voice)
#    - Replace REPLACE_ME_BRAND_NAME with your company name (used in classifier system prompt)
#    - Replace REPLACE_ME_BRAND_DOMAIN if it appears in source_url
#    - (Optional) Replace PLACEHOLDER_META_PIXEL_ID etc. in prep_capi step if you want
#       to fire Meta/LinkedIn Conversions API events on qualified leads. CAPI steps
#       are gated `run_if_js: return false` until you do.

# 2. Apply:
deepline workflows apply --payload "$(cat workflow.json)" --json
```

The response includes the generated webhook URL. Configure your inbound form (Clay, HubSpot form, Typeform, custom) to POST to that URL.

## Required input fields

```json
{
  "email": "founder@brand.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "website": "https://brand.com",
  "annual_revenue": "$1m-$3m",
  "in_retail": true,
  "retailers": "Whole Foods, Target",
  "step": 2,
  "source_url": "https://example.com/get-started?fbclid=xyz",
  "phone": "5555555555",
  "utm_source": "meta",
  "utm_campaign": "cpg_inbound"
}
```

## Routes + scoring

```
junk filter    → drop (silent)
non_cpg        → polite decline draft, posted to declined channel
revenue $500k  → partner_referral (sub-min, send to partner channel)
score 8+       → create_deal (full path: Slack brief + drafted email + LinkedIn DM)
score 5-7      → manual_review (Slack brief, no draft)
```

Score = cpg(0 or 4) + revenue(0-4) + title(0-3) + retail(0-3, default 3 when locator finds 50+ stores).

## Locator coverage

The detect_locator step recognizes:

| Library | Detection | Endpoint |
|---|---|---|
| Storepoint | `StorepointWidget('XXX')` or `api{N}.storepoint.co/v2/(KEY)` | `/locations` |
| Stockist (map_) | `data-stockist-widget-tag="map_..."` | `/locations/overview.js` (count) + `/locations/search` (data) |
| Stockist (legacy u) | `stockist.co/api/v1/u\d+` | `/locations/all` |
| Storerocket | `api.storerocket.io/api/user/...` | `/api/user/{KEY}/locations` |
| Storemapper | `storemapper.com/widgets/cluster/...` | `/widgets/cluster/{ID}.json` |
| Bullseye | `bullseyelocations.*ClientId=...` | `/RestSearch.svc/DoSearch` |
| Brandify | `aem-api.brandify.com/?clientkey=...` | `/store-locator/store?clientkey={KEY}` |
| Closeby | `closeby.co/embed/<32-char-hex>` | `/embed/{KEY}/locations.json` |

Brands without a widget fall back to `firecrawl_extract` with a structured-output schema.

## Pair with slack-button-listener

Configure your Slack app's interactivity URL to point at the [`slack-button-listener`](../slack-button-listener/) workflow so [Approve & Send] / [Edit] / [Skip] clicks trigger downstream actions.
