# Clay Action → Deepline Tool Mappings

Every Clay action maps to a specific Deepline CLI tool or native play. Use actual tool IDs in every generated script — never generic descriptions.

## ⚠️ Tool Discovery Rule — Read First

**The mapping below is a starting-point reference, not a guarantee.** Deepline adds new tools and occasionally renames them. Before using any tool ID in a script:

1. **Verify the tool exists:** `deepline tools get <tool_id>` — if it errors, the tool doesn't exist.
2. **Find alternatives:** `deepline tools search "<intent>"` (e.g. `"add leads campaign"`, `"email verify"`, `"linkedin posts"`)
3. **Native plays are stable** — `person_linkedin_to_email_waterfall`, `name_and_company_to_email_waterfall`, `cost_aware_first_name_and_domain_to_email_waterfall`, `company_to_contact_by_role_waterfall`, `person_enrichment_from_email_waterfall`. Trust these without verification.
4. **Provider tools can change** — always `deepline tools search` before hardcoding individual provider tool names.

```bash
# Before any script: verify and discover
deepline tools get <tool_id>
deepline tools search "add leads smartlead"
deepline tools search "email validation"
```

---

## Model Translation

| Clay model | Deepline `--with` params | Notes |
|---|---|---|
| `gpt-4.1`, `claude` (clay-argon) | `"model":"sonnet","agent":"claude"` | Complex reasoning, json_mode |
| `gpt-4o-mini`, `gpt-5-mini` | `"model":"haiku","agent":"auto"` | Fast classify/generate |
| `gpt-5-nano` | `"model":"haiku","agent":"auto"` | Cheapest tier |

---

## Complete Action → Tool Mapping

| Clay action key | Deepline tool / native play | Notes |
|---|---|---|
| `enrich-person-with-mixrank-v2` | `leadmagic_profile_search` → `crustdata_person_enrichment` waterfall | See Person Enrichment section |
| `lookup-company-in-other-table` | `run_javascript` (local CSV join) | Export company table to CSV first |
| `lookup-multiple-rows-in-other-table` | `run_javascript` (local CSV join) | Same pattern |
| `chat-gpt-schema-mapper` | `call_ai` haiku, no json_mode | Single-value classification |
| `normalize-company-name` | `call_ai` haiku or `run_javascript` | JS preferred for pure string ops |
| `generate-email-permutations` | `run_javascript` | Pure compute, no provider |
| `validate-email` (all instances) | `leadmagic_email_validation` (one final gate) | Skip per-step validation; validate once after waterfall |
| `wiza-find-email` | `dropleads_email_finder` (waterfall step 1) | Part of native play |
| `find-email-v2` (Hunter) | `hunter_email_finder` (waterfall step 2) | Part of native play |
| `leadmagic-find-work-email` | `leadmagic_email_finder` (waterfall step 3) | Part of native play |
| `findymail-find-work-email` | `dropleads_email_finder` (waterfall fallback) | Covered by native play |
| `enrich-person` (PDL) | `peopledatalabs_enrich_contact` (waterfall step) | Covered by native play |
| `dropcontact-enrich-person` | `dropleads_email_finder` (waterfall step) | Covered by native play |
| **Entire email waterfall group** | `person_linkedin_to_email_waterfall` | One play replaces all 6 finders |
| `use-ai` (no web, simple) | `call_ai` haiku | Match model tier |
| `use-ai` (no web, json_mode) | `call_ai` sonnet + `json_mode` schema | |
| `use-ai` (claygent + web) | Pass 1: `call_ai` haiku + `"allowed_tools":"WebSearch"` → Pass 2: `call_ai` sonnet | Always 2 passes, never combine |
| `octave-qualify-person` | `call_ai` sonnet, ICP scoring prompt, `json_mode` | See Octave section |
| `octave-enrich-person` | `call_ai` sonnet + `"allowed_tools":"WebSearch"` | |
| `octave-run-sequence-runner` | Pass 1: `call_ai` haiku (signals) → Pass 2: `call_ai` sonnet (email) | Always 2 passes |
| `social-posts-get-post-activity-posts-and-shares` | `apify_run_actor_sync` with `apimaestro/linkedin-profile-scraper` | Run-as-button in Clay — omit unless user needs posts |
| `score-your-data` (unconfigured) | `run_javascript` keyword scoring | See Scoring section |
| `add-lead-to-campaign` (Smartlead) | `smartlead_add_leads_to_campaign` | |
| `add-lead-to-campaign` (Instantly) | `instantly_add_contacts_to_campaign` | |
| `exa_search` (Clay native) | `exa_search` | Direct equivalent |

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
const fs = require('fs');
const rows = fs.readFileSync(process.env.COMPANY_CSV_PATH, 'utf8')
  .trim().split('\n').slice(1)
  .map(line => JSON.parse(line)); // adjust for CSV parsing
const domain = row['company_domain'];
return rows.find(c => c.domain === domain) || null;
```

```bash
--with '{"alias":"company_data","tool":"run_javascript","payload":{"code":"@$WORKDIR/join_company.js"}}'
```

---

## Email Waterfall (6 Clay providers → 1 Deepline native play)

The entire Clay waterfall group collapses to one native play. Pick based on available input:

**Have LinkedIn URL + name + domain** (preferred — highest hit rate):
```bash
--with '{"alias":"work_email","tool":"person_linkedin_to_email_waterfall","payload":{"linkedin_url":"{{linkedin_url}}","first_name":"{{first_name}}","last_name":"{{last_name}}","domain":"{{company_domain}}"}}'
```
Compiles to: `dropleads_email_finder → hunter_email_finder → leadmagic_email_finder → deepline_native_enrich_contact → crustdata_person_enrichment → peopledatalabs_enrich_contact`

**Have name + company only**:
```bash
--with '{"alias":"work_email","tool":"name_and_company_to_email_waterfall","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","company_name":"{{company_name}}","domain":"{{company_domain}}"}}'
```

**Have first + last + domain only** (cost-efficient — tries pattern validation first):
```bash
--with '{"alias":"work_email","tool":"cost_aware_first_name_and_domain_to_email_waterfall","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","domain":"{{company_domain}}"}}'
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

| Status | Meaning | Bounce rate | Charge |
|---|---|---|---|
| `valid` | Verified deliverable | <1% | Yes |
| `valid_catch_all` | Catch-all domain; engagement data confirms address | <5% | Yes |
| `catch_all` | Domain accepts all; unverifiable | Unknown | **Free** |
| `unknown` | Mail server no response | Unknown | **Free** |
| `invalid` | Will bounce | ~100% | Yes |

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
const first  = (row['first_name']  || '').toLowerCase().replace(/[^a-z]/g, '');
const last   = (row['last_name']   || '').toLowerCase().replace(/[^a-z]/g, '');
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

Prefer `cost_aware_first_name_and_domain_to_email_waterfall` over manual permutations — it includes pattern validation built-in.

---

## Company Name Normalization

### `normalize-company-name`
For LLM-quality normalization:
```bash
--with '{"alias":"normalized_company","tool":"call_ai","payload":{"prompt":"Normalize this company name: {{company_raw}}. Strip legal suffixes (Inc, LLC, Corp, Ltd, Holdings, Group). Return title case. Return ONLY the name, nothing else.","model":"haiku","agent":"auto"}}'
```

For pure string normalization (cheaper):
```javascript
// $WORKDIR/normalize_company.js
const name = row['company_raw'] || '';
return name.replace(/\b(Inc\.?|LLC\.?|Corp\.?|Ltd\.?|Limited|Co\.?|Group|Holdings?)\b/gi, '').trim();
```

---

## Classification

### `chat-gpt-schema-mapper`
```bash
--with '{"alias":"job_function","tool":"call_ai","payload":{"prompt":"Classify this job title into a function label. Rules: all lowercase except BizOps/RevOps/GTM Ops, <4 words, describe the vertical. Return ONLY the label.\n\nJob title: {{job_title}}","model":"haiku","agent":"auto"}}'
```

No `json_mode` needed for single-value string output.

---

## AI Columns — No Web

### `use-ai` (useCase: `use-ai`, no web tools)
```bash
# haiku (gpt-4o-mini / gpt-5-mini equivalent)
--with '{"alias":"data_warehouse_formatted","tool":"call_ai","payload":{"prompt":"<exact Clay prompt with {{field}} refs translated>","model":"haiku","agent":"auto"}}'

# sonnet + json_mode (gpt-4.1 with answerSchemaType equivalent)
--with '{"alias":"strategic_summary","tool":"call_ai","payload":{"prompt":"<prompt>","model":"sonnet","agent":"claude","json_mode":{"type":"object","properties":{"response":{"type":"string"},"top_5_initiatives":{"type":"string"},"top_3_sales_initiatives":{"type":"string"}}}}}'
```

Reference json_mode output in downstream passes as `{{col_name.extracted_json}}`, not `{{col_name.field}}`.

---

## AI Columns — Claygent (Web Research)

### `use-ai` (useCase: `claygent` or web browsing enabled)

**Always two passes.** Never combine research + generation in one `call_ai` — causes timeouts (~40% failure rate on web+generation combined).

**Pass 1 — Research:**
```bash
--with '{"alias":"company_research","tool":"call_ai","payload":{"prompt":"Research {{company_domain}} ({{company_name}}). Find: top strategic initiatives, recent news, GTM signals. Return JSON: {summary, initiatives, recent_news, sources}","model":"haiku","agent":"claude","allowed_tools":"WebSearch","json_mode":{"type":"object","properties":{"summary":{"type":"string"},"initiatives":{"type":"string"},"recent_news":{"type":"string"},"sources":{"type":"string"}}}}}'
```

**Alternative research via exa_search** (deterministic, auditable):
```bash
--with '{"alias":"exa_research","tool":"exa_search","payload":{"query":"{{company_name}} {{company_domain}} strategic initiatives GTM 2024 2025","num_results":5,"contents":{"text":true,"highlights":true}}}'
```

**Pass 2 — Generation (separate `deepline enrich --in-place` call):**
```bash
deepline enrich --input enriched.csv --in-place --rows 0:1 \
  --with '{"alias":"strategic_initiatives","tool":"call_ai","payload":{"prompt":"<Clay prompt translated>\n\nResearch context:\n{{company_research}}","model":"sonnet","agent":"claude","json_mode":{"type":"object","properties":{"top_5_initiatives":{"type":"string"},"top_3_sales_initiatives":{"type":"string"},"top_3_go_to_market_initiatives":{"type":"string"},"new_products":{"type":"string"},"hypothesis_of_potential_challenges":{"type":"string"}}}}}'
```

---

## Octave Actions (proprietary — replace with call_ai)

Octave `ca_*` agents are not externally callable. Always replace with `call_ai` sonnet.

### `octave-qualify-person`
```bash
--with '{"alias":"qualify_person","tool":"call_ai","payload":{"prompt":"Score this prospect against our ICP (0-10 total). ICP: [paste ICP criteria]. Prospect — Title: {{title}}, Company: {{company_name}}, Domain: {{company_domain}}, LinkedIn: {{linkedin_url}}, Initiatives: {{strategic_initiatives}}.\n\nScoring dimensions: persona fit (0-4) + seniority (0-2) + hiring signals (0-2) + strategic fit (0-2).\nTier: A=8-10, B=5-7, C=0-4. Qualified if score>=6.\nReturn JSON.","model":"sonnet","agent":"claude","json_mode":{"type":"object","properties":{"score":{"type":"number"},"tier":{"type":"string","enum":["A","B","C"]},"qualified":{"type":"boolean"},"rationale":{"type":"string"},"disqualifiers":{"type":"array","items":{"type":"string"}}}}}}'
```

### `octave-enrich-person`
```bash
--with '{"alias":"person_enriched","tool":"call_ai","payload":{"prompt":"Research this person using public sources. Name: {{first_name}} {{last_name}}, Title: {{title}}, Company: {{company_name}}, LinkedIn: {{linkedin_url}}. Return JSON with background, career_summary, notable_achievements.","model":"sonnet","agent":"claude","allowed_tools":"WebSearch","json_mode":{"type":"object","properties":{"background":{"type":"string"},"career_summary":{"type":"string"},"notable_achievements":{"type":"string"}}}}}'
```

### `octave-run-sequence-runner` (email generation)
Two passes:

**Pass 1 — Gather signals (separate enrich call):**
```bash
--with '{"alias":"sequence_signals","tool":"call_ai","payload":{"prompt":"Summarize outbound signals for {{first_name}} ({{title}} at {{company_name}}). Use context: {{qualify_person}} / {{strategic_initiatives}} / {{tension_mapping}}. Return key talking points and pain hypotheses.","model":"haiku","agent":"claude"}}'
```

**Pass 2 — Write email:**
```bash
--with '{"alias":"email_sequence","tool":"call_ai","payload":{"prompt":"Write a cold email (subject + body, body <70 words). Recipient: {{first_name}}, {{title}}, {{company_name}}. Signals: {{sequence_signals}}. Tone: casual, direct. No buzzwords.","model":"sonnet","agent":"claude","json_mode":{"type":"object","properties":{"subject":{"type":"string"},"body":{"type":"string"}}}}}'
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
Replace with `run_javascript` keyword scorer:

```javascript
// $WORKDIR/score_row.js
let score = 0;
const title   = (row['job_title'] || '').toLowerCase();
const hiring  = (row['marketing_ops_titles'] || '').toLowerCase();
const dw      = row['data_warehouse_used'];
if (['biz ops','rev ops','operations','bizops','revops'].some(k => title.includes(k))) score += 3;
if (hiring && hiring.length > 10) score += 2;
if (dw) score += 2;
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

| Platform | Tool | Notes |
|---|---|---|
| HeyReach (LinkedIn sequences) | `heyreach_add_to_campaign` | LinkedIn outreach sequences |
| Lemlist | `lemlist_add_to_campaign` | Multi-channel sequences |
| Smartlead (verify tool schema) | `deepline tools get smartlead_api_request` | Use API request endpoint |

---

## Field Reference Translation

Clay uses `{{f_0sy80p3xxx}}` field IDs in prompts. Steps to translate:

1. Get field list from `GET /v3/tables/{TABLE_ID}` (fields[].id + fields[].name)
2. Build map: `f_0sy80p3xxx` → `snake_case(field.name)`
3. After flatten pass: most fields available as `{{fields.xxx}}`
4. `call_ai` json_mode output → always reference as `{{col_name.extracted_json}}` downstream

## Column Naming Convention

```
clay_record                 raw bulk-fetch-records output (run_javascript fetch)
fields                      flattened clay_record subfields (run_javascript flatten)
person_profile              LinkedIn enrichment (leadmagic_profile_search)
company_data                company table join (run_javascript local CSV)
email_permutations          pattern guesses (run_javascript)
work_email                  waterfall winner (person_linkedin_to_email_waterfall)
email_valid                 validation (leadmagic_email_validation)
job_function                classification (call_ai haiku)
normalized_company          normalized name (call_ai haiku)
company_research            web research (call_ai haiku + WebSearch or exa_search)
strategic_initiatives       initiatives JSON (call_ai sonnet, json_mode)
tech_readiness_question     hiring signal question (call_ai haiku)
gtm_friction_question       GTM question (call_ai haiku)
tension_mapping             F.I.N.D. tensions (call_ai sonnet, json_mode)
pvp_messages                value promises (call_ai sonnet, json_mode)
qualify_person              ICP score (call_ai sonnet, json_mode)
sequence_signals            pre-email signals (call_ai haiku)
email_sequence              subject + body (call_ai sonnet, json_mode)
```
