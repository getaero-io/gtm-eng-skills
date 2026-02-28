# Keyword Catalog Reference

The analysis script requires three JSON config files: keywords, tools, and job roles. This reference explains each format and provides generation guidance for ANY vertical.

**CRITICAL: Do NOT copy these examples directly. Generate configs based on your target's vertical (Step 0 + 0.5 discovery).**

## How Matching Works

- **Substring matching**: `integrat` matches "integrate", "integration", "integrations"
- **Case insensitive**: All matching is lowercased
- **Category grouping**: Keywords are grouped by category for structured output

## JSON Format: Keywords (`--keywords`)

Each key is a category name, each value is a list of keyword strings.

### Universal Categories (work across all verticals)

```json
{
  "business_model": [
    "contact sales", "plan", "enterprise", "pricing", "demo",
    "request a demo", "subscription", "free trial", "annual", "monthly"
  ],
  "product_integration": [
    "integrat", "workflow", "api", "connect", "customiz", "automat",
    "personaliz", "sync", "sdk", "webhook", "platform"
  ],
  "company_maturity": [
    "compliance", "secur", "leader", "efficien", "case stud",
    "newsroom", "gartner", "forrester", "training", "resource",
    "soc 2", "gdpr", "iso"
  ]
}
```

### Vertical-Specific Categories (generate per target)

**Category types:**
- **Product category terms** — What does the target sell? (e.g., "creative ops", "AR automation", "sales engagement")
- **Buyer pain points** — What problems does the buyer have? (e.g., "manual invoicing", "fragmented tools", "pipeline visibility")
- **Anti-fit signals** — Competitor names, wrong business model indicators

### Multi-Vertical Examples

**Creative Ops / DAM Tools** (e.g., Bynder, Widen, Brandfolder):
```json
{
  "creative_operations": [
    "creative ops", "creative operations", "asset management", "DAM",
    "content library", "brand guidelines", "creative workflow"
  ],
  "buyer_pain_points": [
    "fragmented tools", "content discovery", "version control",
    "creative approval", "asset organization", "brand consistency"
  ],
  "anti_fit": [
    "bynder", "widen", "brandfolder", "canto", "dam platform"
  ]
}
```

**AR Automation / Finance Tools** (e.g., Tesorio, HighRadius):
```json
{
  "finance_operations": [
    "accounts receivable", "collections", "dunning", "DSO",
    "invoice", "payment", "cash flow", "ar automation"
  ],
  "buyer_pain_points": [
    "manual invoicing", "payment delays", "late payments",
    "cash application", "reconciliation", "aging report"
  ],
  "anti_fit": [
    "highradius", "tesorio", "invoiced", "ar automation platform"
  ]
}
```

**Sales Engagement Tools** (e.g., Outreach, SalesLoft):
```json
{
  "sales_operations": [
    "crm", "salesforce", "prospect", "productiv",
    "onboard", "sequenc", "outbound", "pipeline", "quota"
  ],
  "buyer_pain_points": [
    "manual outreach", "email tracking", "cadence management",
    "activity logging", "pipeline visibility"
  ],
  "anti_fit": [
    "outreach", "salesloft", "apollo", "sales engagement platform"
  ]
}
```

**Developer Tools** (e.g., LaunchDarkly, Vercel):
```json
{
  "developer_operations": [
    "feature flag", "deployment", "ci/cd", "dev experience",
    "build time", "developer productivity", "infrastructure"
  ],
  "buyer_pain_points": [
    "slow builds", "deploy risk", "rollback", "canary deploy",
    "environment management", "developer friction"
  ],
  "anti_fit": [
    "launchdarkly", "vercel", "netlify", "feature flag platform"
  ]
}
```

### Generation Pattern

**1. Product category keywords** — Web search: "{target product category} keywords terminology"

Example for creative ops:
```bash
WebSearch: "creative operations terminology DAM asset management keywords"
```

**2. Buyer pain point keywords** — Web search: "{buyer persona} challenges problems pain points"

Example for creative teams:
```bash
WebSearch: "creative teams marketing teams challenges problems workflow"
```

**3. Anti-fit keywords** — From Step 0.5 competitor discovery

**4. Universal keywords** — Use business_model, product_integration, company_maturity (same across verticals)

## JSON Format: Tech Stack Tools (`--tools`)

Each key is a tool category, each value is a list of tool names to search for. **Niche tools are far more discriminative than generic ones.**

### Multi-Vertical Examples

**Creative / Marketing Tools Stack** (for DAM, creative ops tools):
```json
{
  "creative_design": [
    "figma", "sketch", "adobe creative cloud", "canva", "invision"
  ],
  "marketing_ops": [
    "hubspot", "marketo", "contentful", "wordpress", "webflow"
  ],
  "project_management": [
    "monday.com", "asana", "jira", "clickup", "notion"
  ],
  "video_production": [
    "frame.io", "vimeo", "wistia", "loom"
  ],
  "anti_fit_tech": [
    "bynder", "widen", "brandfolder"
  ]
}
```

**Finance / AR Tools Stack** (for AR automation, billing tools):
```json
{
  "erp_accounting": [
    "netsuite", "quickbooks", "xero", "sage intacct"
  ],
  "crm_billing": [
    "salesforce", "hubspot", "chargebee", "stripe billing"
  ],
  "payment_processing": [
    "stripe", "ach", "paypal", "adyen"
  ],
  "reporting_bi": [
    "tableau", "looker", "power bi", "metabase"
  ],
  "anti_fit_tech": [
    "highradius", "tesorio", "invoiced"
  ]
}
```

**Sales Tools Stack** (for sales engagement, revenue tools):
```json
{
  "crm": [
    "salesforce", "hubspot", "pipedrive"
  ],
  "sales_engagement": [
    "outreach", "salesloft", "apollo", "lemlist"
  ],
  "conversation_intelligence": [
    "gong", "chorus", "clari"
  ],
  "prospecting": [
    "zoominfo", "apollo", "clearbit", "lusha"
  ],
  "anti_fit_tech": [
    "outreach", "salesloft", "sales engagement"
  ]
}
```

**Developer Tools Stack** (for dev tools, infrastructure):
```json
{
  "cloud_infra": [
    "aws", "gcp", "azure", "vercel", "netlify"
  ],
  "ci_cd": [
    "github actions", "gitlab ci", "circle ci", "jenkins"
  ],
  "monitoring": [
    "datadog", "new relic", "pagerduty", "sentry"
  ],
  "feature_flags": [
    "launchdarkly", "split", "optimizely"
  ],
  "anti_fit_tech": [
    "launchdarkly", "vercel", "feature flag"
  ]
}
```

### Generation Pattern

**1. Tech stack discovery** — From Step 0.5 web search: "{buyer persona} common tools tech stack"

Example for creative teams:
```bash
WebSearch: "creative teams marketing teams software tools tech stack"
WebSearch: "creative operations teams figma adobe integrations"
```

**2. Category organization** — Group tools by function (design, marketing, project mgmt, etc.)

**3. Anti-fit tech** — Competitor products from Step 0.5

### Anti-Fit Tech

Include tools that signal the prospect is NOT a good buyer:
- **Competing products** — Bynder/Widen for DAM tools, Outreach/SalesLoft for sales tools
- **Wrong business model** — Shopify for B2B tools (indicates B2C e-commerce)
- **Substitute solutions** — Tools that solve the same problem differently

## JSON Format: Job Roles (`--job-roles`)

Each key is a role category, each value is a list of substrings to match against job titles and descriptions.

### Multi-Vertical Examples

**Creative / Marketing Roles** (for DAM, creative ops tools):
```json
{
  "creative_leadership": ["creative director", "head of creative", "vp creative"],
  "content_management": ["content manager", "content director", "brand manager"],
  "creative_ops": ["creative operations", "creative ops manager", "brand operations"],
  "marketing_ops": ["marketing operations", "marops", "marketing ops manager"],
  "design": ["product designer", "brand designer", "visual designer"],
  "marketing_general": ["marketing manager", "demand gen", "growth marketing"]
}
```

**Finance / Accounting Roles** (for AR automation, billing tools):
```json
{
  "finance_leadership": ["cfo", "vp finance", "head of finance"],
  "ar_collections": ["accounts receivable", "ar manager", "collections manager"],
  "accounting": ["accountant", "controller", "staff accountant"],
  "billing_ops": ["billing manager", "billing operations", "revenue operations"],
  "treasury": ["treasury", "cash management", "financial analyst"]
}
```

**Sales Roles** (for sales engagement, revenue tools):
```json
{
  "sales_leadership": ["cro", "vp sales", "head of sales"],
  "ae": ["account executive", "ae ", "sales executive"],
  "sdr_bdr": ["sdr", "bdr", "sales development", "business development representative"],
  "sales_ops": ["sales operations", "sales ops", "revenue operations", "revops"],
  "enablement": ["enablement", "sales enablement"],
  "customer_success": ["customer success", "cs manager", "csm"]
}
```

**Engineering / Product Roles** (for dev tools, infrastructure):
```json
{
  "engineering_leadership": ["cto", "vp engineering", "head of engineering"],
  "platform_infra": ["platform engineer", "infrastructure engineer", "devops", "sre"],
  "backend": ["backend engineer", "software engineer", "full stack"],
  "frontend": ["frontend engineer", "web developer"],
  "product": ["product manager", "product lead", "product design"]
}
```

### Generation Pattern

**1. Job role discovery** — From Step 0.5 web search: "{buyer persona} job titles roles"

Example for creative teams:
```bash
WebSearch: "creative operations job titles creative director content manager"
WebSearch: "companies hiring creative operations brand manager"
```

**2. Category organization** — Group by seniority and function (leadership, IC roles, ops roles)

**3. Include adjacent roles** — Marketing ops for creative tools, sales ops for sales tools

### Customizing Job Roles for Verticals

**Buyer persona determines roles:**
- Creative/marketing tools → creative director, content manager, brand manager
- Finance tools → CFO, AR manager, controller, accountant
- Sales tools → CRO, AE, SDR, RevOps
- Dev tools → CTO, platform engineer, DevOps, SRE

**Always include:**
- Leadership roles (decision makers)
- IC roles (day-to-day users)
- Ops roles (implementation/process owners)
- Adjacent roles (related functions)

## Anti-Fit vs. Migration Opportunity Keywords

**CRITICAL DISTINCTION:**

**Anti-fit keywords** = Structural mismatches that make the company a bad buyer. These should be rare in Won companies.

**Migration keywords** = Competitor tool usage. These companies are valid targets (displacement opportunity), NOT anti-fit.

### Anti-Fit Keywords (True Exclusions)

1. **Competitor product signals** — Company SELLS the same thing the target sells (they're a vendor, not a buyer)
   - Example: "sales engagement platform" for Outreach/SalesLoft target
   - Example: "DAM platform" or "digital asset management platform" for a DAM tool target
   - Example: "AR automation platform" for HighRadius/Tesorio target

2. **Consumer/B2C signals** (for B2B tools) — `shopper`, `checkout`, `cart`, `consumer`, `debit card`

3. **Wrong industry** — `patient` for non-healthcare tools, `student` for non-EdTech

4. **Wrong business model** — `reseller`, `distributor` for direct-sales tools

### Migration Opportunity Keywords (NOT Anti-Fit)

Competitor TOOL names (Bynder, Widen, Outreach, HighRadius, etc.) indicate companies currently using those tools. These are:
- Valid prospecting targets (migration/replacement opportunity)
- Lower priority than greenfield accounts
- Require different messaging (displacement vs. new adoption)

Add these to a separate category for segmentation, NOT exclusion.

## Generation Workflow Summary

**Step 0** — Discover target (what they sell, who they sell to)
**Step 0.5** — Discover ecosystem (competitors, tech stack, job roles)
**Step 1.5** — Generate configs using patterns above

**For keywords.json:**

1. Start with universal categories (business_model, product_integration, company_maturity)
2. Add product category terms from Step 0
3. Add buyer pain points from Step 0.5
4. Add competitor tool names for migration segment (e.g., "bynder", "widen") — NOT anti-fit
5. Add true anti-fit keywords (product signals like "DAM platform", structural mismatches)

**For tools.json:**

1. Organize tech stack from Step 0.5 into categories
2. Focus on niche tools specific to buyer persona
3. Add competitor tool products for migration segment — NOT anti_fit_tech

**For job-roles.json:**

1. Organize roles from Step 0.5 by seniority/function
2. Include leadership (decision makers), IC (users), ops (implementers)
3. Add adjacent roles related to buyer persona

**Validation (Step 3.5):**

- Check generated keywords appear in enriched data
- Verify job roles match actual job listings
- Ensure tech stack tools match integrations/tech pages
- Confirm product category keywords (what target SELLS) don't appear frequently in Won companies → if they do, those are competitors not buyers
