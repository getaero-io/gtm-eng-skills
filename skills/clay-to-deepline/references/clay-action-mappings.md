# Clay Action → Deepline Tool Mappings

Every Clay action maps to a specific Deepline CLI tool or native play. Use actual tool IDs in every generated script — never generic descriptions.

## ⚠️ Tool Discovery Protocol — Read First

**This mapping is a starting-point reference, not a guarantee.** Deepline adds new tools, native plays, and provider integrations continuously. The right mental model:

**For every Clay action, the selection order is:**

1. **Native play first** — check if a native Deepline play covers the action (they're stable, multi-provider, and cost-optimized). Current native plays: `name_and_domain_to_email_waterfall`, `company_to_contact_by_role_waterfall`, and `contact_to_phone_waterfall`.
2. **Search for a dedicated tool** — `deepline tools search "<intent>"` before hardcoding any individual provider tool. New tools are added regularly. Examples: `deepline tools search "qualify person ICP"`, `deepline tools search "octave"`, `deepline tools search "email verify"`, `deepline tools search "add leads campaign"`.
3. **Verify the tool exists** — `deepline tools get <tool_id>`. If it errors, the tool doesn't exist yet — use the `deeplineagent` fallback from this doc.
4. **Use the mapping below as a fallback** — when no native play or dedicated tool exists.

```bash
# Standard discovery pattern before writing any --with spec
deepline tools search "<action intent>"     # find current options
deepline tools get <candidate_tool_id>      # verify it exists + see payload schema
```

**Why this matters:** Deepline may add a native `octave_qualify_person`, `instantly_send_email`, or other integration at any time. Searching first means your script gets the better tool automatically — instead of being locked into a `deeplineagent` approximation.

---

## Model Translation

| Clay model                       | Deepline `--with` params                | Notes                                            |
| -------------------------------- | --------------------------------------- | ------------------------------------------------ |
| `gpt-4.1`, `claude` (clay-argon) | `"model":"anthropic/claude-sonnet-4.6"` | Complex reasoning, larger structured outputs     |
| `gpt-4.1-mini`                   | `"model":"openai/gpt-5.4-mini"`         | Clay's mid-tier model for claygent-style columns |
| `gpt-4o-mini`, `gpt-5-mini`      | `"model":"openai/gpt-5.4-mini"`         | Fast classify/generate                           |
| `gpt-5-nano`                     | `"model":"openai/gpt-5.4-mini"`         | Cheapest tier approximation                      |

---

## Complete Action → Tool Mapping

| Clay action key                                             | Deepline tool / native play                                                                                                                                                                                                                                                                                                                                                                               | Notes                                                                                              |
| ----------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `find-lists-of-companies-with-mixrank-source` (source type) | **Pass 1**: `apollo_company_search` — filters by location, employee count, industry keywords, tech stack, funding. Returns `name`, `primary_domain`, `linkedin_url`, `city`, `state`, `country`. **Pass 2** (optional): `prospeo_enrich_company` — adds `description`, `employee_count`, `industry`, `type`. Apollo is 0.2 credits/call; Prospeo is 0.6 credits/result. See Company Source section below. | ✅ Tested — apollo_company_search returns 4–100 companies per call with location + keyword filters |
| `enrich-person-with-mixrank-v2`                             | `leadmagic_profile_search` → `crustdata_person_enrichment` waterfall                                                                                                                                                                                                                                                                                                                                      | See Person Enrichment section                                                                      |
| `lookup-company-in-other-table`                             | `run_javascript` (local CSV join)                                                                                                                                                                                                                                                                                                                                                                         | Export company table to CSV first                                                                  |
| `lookup-multiple-rows-in-other-table`                       | `run_javascript` (local CSV join)                                                                                                                                                                                                                                                                                                                                                                         | Same pattern                                                                                       |
| `chat-gpt-schema-mapper`                                    | `deeplineagent`; use `jsonSchema` when you need structured extraction                                                                                                                                                                                                                                                                                                                                     | Single-value classification                                                                        |
| `normalize-company-name`                                    | `deeplineagent` or `run_javascript`                                                                                                                                                                                                                                                                                                                                                                       | JS preferred for pure string ops                                                                   |
| `generate-email-permutations`                               | `run_javascript`                                                                                                                                                                                                                                                                                                                                                                                          | Pure compute, no provider                                                                          |
| `validate-email` (all instances)                            | `leadmagic_email_validation` (one final gate)                                                                                                                                                                                                                                                                                                                                                             | Skip per-step validation; validate once after waterfall                                            |
| `wiza-find-email`                                           | `dropleads_email_finder` (waterfall step 1)                                                                                                                                                                                                                                                                                                                                                               | Part of native play                                                                                |
| `find-email-v2` (Hunter)                                    | `hunter_email_finder` (waterfall step 2)                                                                                                                                                                                                                                                                                                                                                                  | Part of native play                                                                                |
| `leadmagic-find-work-email`                                 | `leadmagic_email_finder` (waterfall step 3)                                                                                                                                                                                                                                                                                                                                                               | Part of native play                                                                                |
| `findymail-find-work-email`                                 | `dropleads_email_finder` (waterfall fallback)                                                                                                                                                                                                                                                                                                                                                             | Covered by native play                                                                             |
| `enrich-person` (PDL)                                       | `peopledatalabs_enrich_contact` (waterfall step)                                                                                                                                                                                                                                                                                                                                                          | Covered by native play                                                                             |
| `dropcontact-enrich-person`                                 | `dropleads_email_finder` (waterfall step)                                                                                                                                                                                                                                                                                                                                                                 | Covered by native play                                                                             |
| **Entire email waterfall group**                            | `name_and_domain_to_email_waterfall`                                                                                                                                                                                                                                                                                                                                                                      | One play replaces all 6 finders when you have a domain; include `linkedin_url` when available      |
| `use-ai` (no web, simple)                                   | `deeplineagent`                                                                                                                                                                                                                                                                                                                                                                                           | Match model tier                                                                                   |
| `use-ai` (no web, structured)                               | `deeplineagent` + `jsonSchema`                                                                                                                                                                                                                                                                                                                                                                            |                                                                                                    |
| `use-ai` (claygent + web)                                   | Pass 1: `exa_search` → Pass 2: `deeplineagent`                                                                                                                                                                                                                                                                                                                                                            | Always split research and synthesis                                                                |
| `octave-qualify-person`                                     | `deeplineagent`, ICP scoring prompt, `jsonSchema`                                                                                                                                                                                                                                                                                                                                                         | See Octave section                                                                                 |
| `octave-enrich-person`                                      | `exa_search` + `deeplineagent`                                                                                                                                                                                                                                                                                                                                                                            |                                                                                                    |
| `octave-run-sequence-runner`                                | Pass 1: `deeplineagent` (signals) → Pass 2: `deeplineagent` (email)                                                                                                                                                                                                                                                                                                                                       | Always 2 passes                                                                                    |
| `social-posts-get-post-activity-posts-and-shares`           | `apify_run_actor_sync` with `apimaestro/linkedin-profile-scraper`                                                                                                                                                                                                                                                                                                                                         | Run-as-button in Clay — omit unless user needs posts                                               |
| `score-your-data` (unconfigured)                            | `run_javascript` keyword scoring                                                                                                                                                                                                                                                                                                                                                                          | See Scoring section                                                                                |
| `add-lead-to-campaign` (Smartlead)                          | `smartlead_add_leads_to_campaign`                                                                                                                                                                                                                                                                                                                                                                         |                                                                                                    |
| `add-lead-to-campaign` (Instantly)                          | `instantly_add_contacts_to_campaign`                                                                                                                                                                                                                                                                                                                                                                      |                                                                                                    |
| `exa_search` (Clay native)                                  | `exa_search`                                                                                                                                                                                                                                                                                                                                                                                              | Direct equivalent                                                                                  |

---

## Person Enrichment (LinkedIn URL → profile data)

### `enrich-person-with-mixrank-v2`

**Best single tool** — `leadmagic_profile_search`:

```bash
--with '{"alias":"person_profile","tool":"leadmagic_profile_search","payload":{"profile_url":"{{linkedin_url}}"}}'
```

Key output paths: `.data.full_name`, `.data.work_experience[0].company_website`, `.data.company_website`

**Richer fallback** — `crustdata_person_enrichment`:

```bash
--with '{"alias":"person_profile","tool":"crustdata_person_enrichment","payload":{"linkedinProfileUrl":"{{linkedin_url}}"}}'
```

Key output paths: `.data[0].name`, `.data[0].email`, `.data[0].current_employers[0].employer_company_website_domain[0]`

**Work history / posts** — Apify (structured, free):

```bash
deepline tools execute apify_run_actor_sync --payload '{"actorId":"apimaestro/linkedin-profile-scraper","input":{"profileUrls":["{{linkedin_url}}"]},"timeoutMs":60000}'
```

---

## Company Table Lookup (Clay cross-table join)

### `lookup-company-in-other-table` / `lookup-multiple-rows-in-other-table`

Export the linked Clay table to a local CSV first (`clay_fetch_records.sh` schema mode). Then join with `run_javascript`:

```javascript
// $WORKDIR/join_company.js
// Adjust field names to match your table's column aliases
const fs = require('fs');
const rows = fs
  .readFileSync(process.env.COMPANY_CSV_PATH, 'utf8')
  .trim()
  .split('\n')
  .slice(1)
  .map((line) => JSON.parse(line)); // adjust for CSV format
const joinKey = row['company_domain'] || row['domain']; // ← your join key column
return rows.find((c) => c.domain === joinKey) || null;
```

```bash
--with '{"alias":"company_data","tool":"run_javascript","payload":{"code":"@$WORKDIR/join_company.js"}}'
```

---

## Email Waterfall (6 Clay providers → 1 Deepline native play)

The entire Clay waterfall group collapses to one native play. Pick based on available input:

**Have LinkedIn URL + name + domain** (preferred — highest hit rate):

```bash
--with '{"alias":"work_email","tool":"name_and_domain_to_email_waterfall","payload":{"linkedin_url":"{{linkedin_url}}","first_name":"{{first_name}}","last_name":"{{last_name}}","domain":"{{company_domain}}"}}'
```

Compiles to: `dropleads_email_finder → hunter_email_finder → leadmagic_email_finder → deepline_native_enrich_contact → crustdata_person_enrichment → peopledatalabs_enrich_contact`

**Have name + company only**:

```bash
--with '{"alias":"work_email","tool":"name_and_domain_to_email_waterfall","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","domain":"{{company_domain}}"}}'
```

**Have first + last + domain only** (cost-efficient — tries pattern validation first):

```bash
--with '{"alias":"work_email","tool":"name_and_domain_to_email_waterfall","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","domain":"{{domain}}"}}'
```

Compiles to: `leadmagic_email_validation (first.last@, firstlast@, first_last@) → dropleads_email_finder → hunter_email_finder → leadmagic_email_finder → deepline_native_enrich_contact → peopledatalabs_enrich_contact`

**Alternative individual providers** (use `deepline tools search "email"` to see current list):

- `icypeas_email_finder` — 700M+ profiles, strong LinkedIn coverage; useful as a step if native play misses
- `dropleads_email_finder` — included in native plays; available standalone too
- Run `deepline tools get icypeas_email_finder` to verify tool exists before using

**Final validation gate** (replaces all per-step Clay `validate-email` calls):

Default — `leadmagic_email_validation`:

```bash
--with '{"alias":"email_valid","tool":"leadmagic_email_validation","payload":{"email":"{{work_email}}"}}'
```

LeadMagic returns four relevant statuses (as `.data.email_status`):

| Status            | Meaning                                            | Bounce rate | Charge   |
| ----------------- | -------------------------------------------------- | ----------- | -------- |
| `valid`           | Verified deliverable                               | <1%         | Yes      |
| `valid_catch_all` | Catch-all domain; engagement data confirms address | <5%         | Yes      |
| `catch_all`       | Domain accepts all; unverifiable                   | Unknown     | **Free** |
| `unknown`         | Mail server no response                            | Unknown     | **Free** |
| `invalid`         | Will bounce                                        | ~100%       | Yes      |

**Accept `valid`, `valid_catch_all`, AND `catch_all` as "found"** — all three are as reliable as what Clay reports. `valid_catch_all` is the highest-confidence version (LeadMagic has engagement signal data for the address). Do not accept `unknown`.

Alternative — `zerobounce_validate` (more detailed sub_status, better for catch-all domains):

```bash
--with '{"alias":"email_valid","tool":"zerobounce_validate","payload":{"email":"{{work_email}}"}}'
```

Check `.status` and `.sub_status`. Use `zerobounce_batch_validate` for 5+ emails in one call.

Alternative — `dropleads_email_verifier` (cheapest option):

```bash
--with '{"alias":"email_valid","tool":"dropleads_email_verifier","payload":{"email":"{{work_email}}"}}'
```

Run `deepline tools search "email validation"` to see all current options.

---

## Email Permutations

### `generate-email-permutations`

Pure `run_javascript` — no provider:

```javascript
// $WORKDIR/email_permutations.js
const first = (row['first_name'] || '').toLowerCase().replace(/[^a-z]/g, '');
const last = (row['last_name'] || '').toLowerCase().replace(/[^a-z]/g, '');
const domain = row['company_domain'] || '';
if (!first || !last || !domain) return null;
const perms = [
  `${first}.${last}@${domain}`,
  `${first}${last}@${domain}`,
  `${first}_${last}@${domain}`,
  `${first}@${domain}`,
  `${first[0]}${last}@${domain}`,
  `${first}${last[0]}@${domain}`,
  `${first[0]}.${last}@${domain}`,
  `${last}.${first}@${domain}`,
];
return { permutations: perms, comma_separated_list: perms.join(',') };
```

```bash
--with '{"alias":"email_permutations","tool":"run_javascript","payload":{"code":"@$WORKDIR/email_permutations.js"}}'
```

Prefer `name_and_domain_to_email_waterfall` over a hand-built waterfall when you already have a clean company domain.

---

## Company Source — Replacing `find-lists-of-companies-with-mixrank-source`

Clay's Mixrank source fetches a pre-built list from a configured Mixrank query. The Deepline equivalent is a two-pass Python script: **discover with `apollo_company_search`**, then **enrich with `prospeo_enrich_company`** for fields Clay gets from Mixrank (description, industry, size, type).

### Pass 1 — Generate company list (`apollo_company_search`)

```python
import json, subprocess, csv

# Apollo filter payload — translate from Clay's Mixrank source config
# Check the Clay table config or ask the user for the original filter criteria
payload = {
    "organization_locations": ["Los Angeles", "San Diego", "Orange County", "Irvine"],  # example: SouthernCal
    "q_organization_keyword_tags": ["software", "technology", "saas"],                   # industry focus
    "organization_num_employees_ranges": ["51,200", "201,500", "501,1000"],              # size range
    # "currently_using_any_of_technology_uids": ["snowflake", "bigquery"],              # tech stack (optional)
    "per_page": 100,
    "page": 1,   # increment for more pages
}

result = subprocess.run(
    ["deepline", "tools", "execute", "apollo_company_search",
     "--payload", json.dumps(payload), "--json"],
    capture_output=True, text=True
)
data = json.loads(result.stdout)
companies = data.get("result", {}).get("accounts", [])
# Fields: name, primary_domain, linkedin_url, organization_city, organization_state,
#         organization_country, organization_revenue_printed
```

**Apollo output → Clay field mapping:**

| Apollo field                               | Clay formula field                                      |
| ------------------------------------------ | ------------------------------------------------------- |
| `name`                                     | Name                                                    |
| `primary_domain`                           | Domain                                                  |
| `linkedin_url`                             | LinkedIn URL                                            |
| `organization_city` + `organization_state` | Location                                                |
| `organization_country`                     | Country                                                 |
| —                                          | Size, Description, Primary Industry, Type (need Pass 2) |

### Pass 2 — Enrich missing fields (`prospeo_enrich_company`, optional)

Only needed if downstream passes reference `Description`, `Primary Industry`, `Size`, or `Type`.

```python
# For each company from Pass 1 that lacks description/industry:
result = subprocess.run(
    ["deepline", "tools", "execute", "prospeo_enrich_company",
     "--payload", json.dumps({"website": domain}), "--json"],
    capture_output=True, text=True
)
enriched = json.loads(result.stdout).get("result", {}).get("company", {})
# Fields: description, employee_count, employee_range (= Size), industry categories, company_type
```

### Cost comparison

| Clay                                          | Deepline                                                                                            |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Mixrank source — bundled in Clay subscription | Apollo: 0.2 credits/call (100 companies per call = 0.002/company) + Prospeo: 0.6 credits/enrichment |
| Returns all fields in one step                | Two passes; Pass 2 optional if downstream uses only domain/name/linkedin                            |

### Key questions to ask the user before generating the script

1. What filters did the Clay Mixrank source use? (location, size, industry, tech stack) — visible in the Clay source config or ask the user
2. How many companies total? (Apollo paginates at 100/page, max 500 pages)
3. Does the pipeline actually use `Description`, `Industry`, `Size`, `Type`? If not, skip Pass 2.

---

## Company Name Normalization

### `normalize-company-name`

For LLM-quality normalization:

```bash
--with '{"alias":"normalized_company","tool":"deeplineagent","payload":{"model":"openai/gpt-5.4-mini","prompt":"Normalize this company name: {{company_raw}}. Strip legal suffixes (Inc, LLC, Corp, Ltd, Holdings, Group). Return title case. Return ONLY the name, nothing else."}}'
```

For pure string normalization (cheaper):

```javascript
// $WORKDIR/normalize_company.js
const name = row['company_raw'] || '';
return name
  .replace(
    /\b(Inc\.?|LLC\.?|Corp\.?|Ltd\.?|Limited|Co\.?|Group|Holdings?)\b/gi,
    '',
  )
  .trim();
```

---

## Classification

### `chat-gpt-schema-mapper`

```bash
--with '{"alias":"job_function","tool":"deeplineagent","payload":{"model":"openai/gpt-5.4-mini","prompt":"Classify this job title into a function label. Rules: all lowercase except BizOps/RevOps/GTM Ops, <4 words, describe the vertical. Return ONLY the label.\n\nJob title: {{job_title}}"}}'
```

No `jsonSchema` needed for a single-value string output.

---

## AI Columns — No Web

### `use-ai` (useCase: `use-ai`, no web tools)

```bash
# fast reasoning / generation
--with '{"alias":"data_warehouse_formatted","tool":"deeplineagent","payload":{"model":"openai/gpt-5.4-mini","prompt":"<exact Clay prompt with {{field}} refs translated>"}}'

# larger structured output
--with '{"alias":"strategic_summary","tool":"deeplineagent","payload":{"model":"anthropic/claude-sonnet-4.6","prompt":"<prompt>","jsonSchema":{"type":"object","properties":{"response":{"type":"string"},"top_5_initiatives":{"type":"string"},"top_3_sales_initiatives":{"type":"string"}},"required":["response"],"additionalProperties":false}}}'
```

Reference structured output fields in downstream passes as `{{col_name.field}}`. If you need deeper nesting, flatten it first.

---

## AI Columns — Claygent (Web Research)

### `use-ai` (useCase: `claygent` or web browsing enabled)

**Always two passes.** Never combine broad research + generation in one model step — it is harder to debug and less stable than a split search/synthesis flow.

**Pass 1 — Research:**

```bash
--with '{"alias":"company_research","tool":"deeplineagent","payload":{"model":"openai/gpt-5.4-mini","prompt":"Use the research context to summarize {{company_domain}} ({{company_name}}). Return JSON with summary, initiatives, and sources.","jsonSchema":{"type":"object","properties":{"summary":{"type":"string"},"initiatives":{"type":"string"},"sources":{"type":"string"}},"required":["summary","initiatives"],"additionalProperties":false}}}'
```

**Alternative research via exa_search** (deterministic, auditable):

```bash
--with '{"alias":"exa_research","tool":"exa_search","payload":{"query":"{{company_name}} {{company_domain}} strategic initiatives GTM 2024 2025","num_results":5,"contents":{"text":true,"highlights":true}}}'
```

**Pass 2 — Generation (separate `deepline enrich --in-place` call):**

```bash
deepline enrich --input enriched.csv --in-place --rows 0:1 \
  --with '{"alias":"strategic_initiatives","tool":"deeplineagent","payload":{"model":"anthropic/claude-sonnet-4.6","prompt":"<Clay prompt translated>\n\nResearch context:\n{{company_research}}","jsonSchema":{"type":"object","properties":{"top_5_initiatives":{"type":"string"},"top_3_sales_initiatives":{"type":"string"},"top_3_go_to_market_initiatives":{"type":"string"},"new_products":{"type":"string"},"hypothesis_of_potential_challenges":{"type":"string"}},"required":["top_5_initiatives"],"additionalProperties":false}}}'
```

---

## Octave Actions (proprietary — search for native equivalent first)

Octave `ca_*` agents are proprietary Clay integrations. Before defaulting to `deeplineagent`, check whether Deepline has added a native equivalent:

```bash
deepline tools search "qualify person ICP"
deepline tools search "octave"
deepline tools search "sequence runner email"
```

If a native tool exists (e.g. `octave_qualify_person`, `octave_sequence_runner`), use it directly — it will be faster and more accurate than the `deeplineagent` fallbacks below. The patterns below are **fallbacks for when no native tool is available**.

### `octave-qualify-person`

```bash
--with '{"alias":"qualify_person","tool":"deeplineagent","payload":{"model":"anthropic/claude-sonnet-4.6","prompt":"Score this prospect against our ICP (0-10 total). ICP: [paste ICP criteria]. Prospect — Title: {{title}}, Company: {{company_name}}, Domain: {{company_domain}}, LinkedIn: {{linkedin_url}}, Initiatives: {{strategic_initiatives}}.\n\nScoring dimensions: persona fit (0-4) + seniority (0-2) + hiring signals (0-2) + strategic fit (0-2).\nTier: A=8-10, B=5-7, C=0-4. Qualified if score>=6.\nReturn JSON.","jsonSchema":{"type":"object","properties":{"score":{"type":"number"},"tier":{"type":"string","enum":["A","B","C"]},"qualified":{"type":"boolean"},"rationale":{"type":"string"},"disqualifiers":{"type":"array","items":{"type":"string"}}},"required":["score","tier","qualified","rationale"],"additionalProperties":false}}}'
```

### `octave-enrich-person`

```bash
--with '{"alias":"person_enriched","tool":"deeplineagent","payload":{"model":"anthropic/claude-sonnet-4.6","prompt":"Research this person using public sources. Name: {{first_name}} {{last_name}}, Title: {{title}}, Company: {{company_name}}, LinkedIn: {{linkedin_url}}. Return JSON with background, career_summary, and notable_achievements.","jsonSchema":{"type":"object","properties":{"background":{"type":"string"},"career_summary":{"type":"string"},"notable_achievements":{"type":"string"}},"required":["background","career_summary"],"additionalProperties":false}}}'
```

### `octave-run-sequence-runner` (email generation)

Two passes:

**Pass 1 — Gather signals (separate enrich call):**

```bash
--with '{"alias":"sequence_signals","tool":"deeplineagent","payload":{"model":"openai/gpt-5.4-mini","prompt":"Summarize outbound signals for {{first_name}} ({{title}} at {{company_name}}). Use context: {{qualify_person}} / {{strategic_initiatives}} / {{tension_mapping}}. Return key talking points and pain hypotheses."}}'
```

**Pass 2 — Write email:**

```bash
--with '{"alias":"email_sequence","tool":"deeplineagent","payload":{"model":"anthropic/claude-sonnet-4.6","prompt":"Write a cold email (subject + body, body <70 words). Recipient: {{first_name}}, {{title}}, {{company_name}}. Signals: {{sequence_signals}}. Tone: casual, direct. No buzzwords.","jsonSchema":{"type":"object","properties":{"subject":{"type":"string"},"body":{"type":"string"}},"required":["subject","body"],"additionalProperties":false}}}'
```

---

## LinkedIn Posts

### `social-posts-get-post-activity-posts-and-shares`

Skip for automation unless explicitly needed (run-as-button in Clay). Two options when needed:

**Option 1 — `crustdata_linkedin_posts` (keyword/filter based):**
Good for finding posts about a company or topic. Filters by `MEMBER` or `COMPANY` LinkedIn filter type. Not profile-URL-specific.

```bash
--with '{"alias":"li_posts","tool":"crustdata_linkedin_posts","payload":{"keyword":"{{company_name}}","filters":[{"filter_type":"AUTHOR_COMPANY","type":"in","value":["{{company_name}}"]}],"limit":5,"datePosted":"past-quarter"}}'
```

**Option 2 — Apify actor (profile-URL-specific):**
Use when you need posts for a specific person's profile URL. Run-as-button in Clay → batch all URLs in one call:

```bash
deepline tools execute apify_run_actor_sync --payload '{
  "actorId": "apimaestro/linkedin-profile-scraper",
  "input": {"profileUrls": ["{{linkedin_url}}"], "scrapePostsInfo": true},
  "timeoutMs": 60000
}'
```

Note: `crustdata_linkedin_posts` is keyword/filter search — it doesn't take a profile URL directly. Use Apify when you need "posts by this specific person".

---

## Scoring

### `score-your-data` (unconfigured — all input slots blank)

Replace with `run_javascript` keyword scorer. **Column names below are placeholders — replace with your actual Clay column aliases from the flatten pass.**

```javascript
// $WORKDIR/score_row.js
// Replace field names with your actual column aliases (from fields.xxx or top-level)
let score = 0;
const title = (row['job_title'] || '').toLowerCase(); // ← your title column
const signal1 = (row['hiring_signal'] || '').toLowerCase(); // ← your first signal column
const signal2 = row['tech_stack']; // ← your second signal column

// Adjust keywords and weights to your ICP scoring criteria
if (['vp', 'director', 'head of'].some((k) => title.includes(k))) score += 3;
if (signal1 && signal1.length > 10) score += 2;
if (signal2) score += 2;

const tier = score >= 7 ? 'A' : score >= 4 ? 'B' : 'C';
return { score, tier };
```

---

## Campaign Activation

### `add-lead-to-campaign` (Smartlead)

`smartlead_add_leads_to_campaign` does **not** exist. Use `smartlead_api_request` to POST to the leads endpoint:

```bash
deepline tools execute smartlead_api_request --payload '{
  "method": "POST",
  "endpoint": "/v1/campaigns/<campaign_id>/leads",
  "data": {
    "lead_list": [
      {
        "email": "{{final_email}}",
        "first_name": "{{first_name}}",
        "last_name": "{{last_name}}",
        "company_name": "{{company_name}}",
        "linkedin_url": "{{linkedin_url}}"
      }
    ]
  }
}'
```

Or inside `deepline enrich`:

```bash
--with '{"alias":"campaign_push","tool":"smartlead_api_request","payload":{"method":"POST","endpoint":"/v1/campaigns/<campaign_id>/leads","data":{"lead_list":[{"email":"{{final_email}}","first_name":"{{first_name}}","last_name":"{{last_name}}","company_name":"{{company_name}}"}]}}}'
```

### `add-lead-to-campaign` (Instantly)

Correct tool name is `instantly_add_to_campaign` (not `instantly_add_contacts_to_campaign`):

```bash
deepline tools execute instantly_add_to_campaign --payload '{
  "campaign_id": "<campaign_id>",
  "leads": [{"email": "{{final_email}}", "first_name": "{{first_name}}", "last_name": "{{last_name}}", "company_name": "{{company_name}}"}]
}'
```

### Other campaign platforms

| Platform                       | Tool                                       | Notes                       |
| ------------------------------ | ------------------------------------------ | --------------------------- |
| HeyReach (LinkedIn sequences)  | `heyreach_add_to_campaign`                 | LinkedIn outreach sequences |
| Lemlist                        | `lemlist_add_to_campaign`                  | Multi-channel sequences     |
| Smartlead (verify tool schema) | `deepline tools get smartlead_api_request` | Use API request endpoint    |

---

## Field Reference Translation

Clay uses `{{f_0sy80p3xxx}}` field IDs in prompts and formula cells. Steps to translate:

1. Get field list from `GET /v3/tables/{TABLE_ID}` → `fields[].id` + `fields[].name`
2. Build the ID→name map: `f_0sy80p3xxx` → `snake_case(field.name)`
3. In recovered prompts, replace every `{{f_xxx}}` with `{{fields.snake_name}}` (post-flatten) or `{{alias}}` (if it's a prior pass output)
4. Fix Clay formula bugs sometimes present in rendered cell values:
   - Wrong field reference: `{{last_name}}` where `{{job_title}}` was intended — cross-check against the column name
   - Unresolved single-brace: `{field_name}` (Clay uses `{{double_braces}}` only) — add the second brace pair
5. Reference rules by output type:

| Source column type                   | Downstream reference                   |
| ------------------------------------ | -------------------------------------- |
| `run_javascript` returning a scalar  | `{{alias}}`                            |
| `run_javascript` returning an object | `{{alias.field_name}}`                 |
| `deeplineagent` without `jsonSchema` | `{{alias}}` (raw string)               |
| `deeplineagent` with `jsonSchema`    | `{{alias.field_name}}` for flat fields |
| Flattened Clay field                 | `{{fields.snake_name}}`                |

**2-level max:** `{{alias.field}}` works; `{{alias.field.nested}}` fails — flatten the nested object first with a `run_javascript` pass.

---

## Column Alias Convention

Aliases **derive from the actual Clay column name**, not from a fixed list:

- Snake_case the Clay column name: "Work Email" → `work_email`, "Strategic Initiatives" → `strategic_initiatives`
- Strip leading/trailing spaces and special characters before snake_casing
- For multi-step patterns (email waterfall fallbacks), append a short functional suffix: `work_email_li` (LinkedIn fallback), `work_email_valid` (validation gate)

**Two reserved structural aliases** (always these names, regardless of Clay column names):

| Alias         | Purpose                                                       |
| ------------- | ------------------------------------------------------------- |
| `clay_record` | Raw bulk-fetch-records output (run_javascript fetch pass)     |
| `fields`      | Flattened clay_record subfields (run_javascript flatten pass) |

**All other aliases come from the Clay schema.** Look up `fields[].name` in `GET /v3/tables/{id}` and snake_case them. Do not invent aliases from any memorized list — if the Clay column is named "Tension Mapping", the alias is `tension_mapping`. If it's named "PVP Messages", it's `pvp_messages`.
