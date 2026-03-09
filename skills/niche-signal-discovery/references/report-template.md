# Report Template Reference

Template for the niche signals report. Follow this structure and quality rules strictly.

**Every report opens with a Quick Reference Dashboard (Sections 1.1–1.5) before the detailed data sections. This lets any reader — AE, SDR, or executive — understand key findings in under 2 minutes and take action immediately.**

---

## Section 1: Quick Reference Dashboard

**Required at the top of every report.** Generate once analysis is complete. Use actual lift scores and signal names from your dataset.

### 1.1 TLDR (5 Bullets)

Format as a prominent callout/highlight block at the very top of the report:

```
⚡ TLDR — Read This First

• #1 signal: [top signal name] on their website — [X]x more common in won accounts — [one-line reason why it indicates buying intent]
• Best-fit archetype: [ideal won customer in one sentence: size, vertical, regulatory context, maturity stage]
• Fastest path to pipeline: Dropleads search for "[title 1]" + "[title 2]" at [headcount]-person [vertical] companies — these people own the buying decision
• Hard skip flags: [signal 1], [signal 2], [signal 3] — [brief reason each signals existing solution, build culture, or procurement freeze]
• Scoring: 60+ pts → Tier 1 immediate outreach · 35–59 → Tier 2 trigger-based · <35 → nurture or skip
```

### 1.2 Signal Strength at a Glance

Two tables with visual lift bars. Sort positive signals by lift descending, anti-fit by lift ascending.

**Lift → Strength Bar scale:**

| Lift | Bar |
|------|-----|
| ≥10x | 🟩🟩🟩🟩🟩🟩 |
| ≥4x | 🟩🟩🟩🟩🟩 |
| ≥2.5x | 🟩🟩🟩🟩 |
| ≥2.0x | 🟩🟩🟩 |
| ≥1.5x | 🟩🟩 |
| ≥1.0x | 🟩 |
| ≥0.4x | 🟥🟥 |
| ≥0.25x | 🟥🟥🟥 |
| ≥0.15x | 🟥🟥🟥🟥 |
| ≥0.07x | 🟥🟥🟥🟥🟥 |
| <0.07x | 🟥🟥🟥🟥🟥🟥 |

**✅ Positive Fit Signals** — Top 10–15, sorted by lift descending:

```markdown
| Signal | Lift | Strength | Source | What to Look For |
|--------|------|----------|--------|------------------|
| [signal name] | [X.Xx] | [bar] | 🌐 Website / 💼 Jobs / 💻 Tech | [1-sentence: what to check and what it means] |
```

Source icons: `🌐 Website` = found in website content · `💼 Jobs` = found in job listings · `💻 Tech` = tech stack detection

**🚫 Anti-Fit Signals** — All signals with lift < 0.5x:

```markdown
| Signal | Lift | Risk | Why |
|--------|------|------|-----|
| [signal name] | [0.Xx] | [bar] | [root cause: existing solution / build culture / procurement freeze / etc.] |
```

### 1.3 Platform Search Recipes

Pre-built, click-ready search links for each buyer type.

**People Searches (find the buyers):**

```markdown
| Who You're Finding | Why They're the Buyer | Dropleads Link |
|--------------------|----------------------|-------------|
| [Title 1, Title 2, Title 3] | [Signal lift + one-line reason they own the decision] | [Open in Dropleads ↗](URL) |
```

**Company Searches (find the accounts):**

```markdown
| What You're Finding | Signal It Represents | Dropleads Link |
|--------------------|---------------------|-------------|
| [Company type + keyword filter] | [Signal name + lift] | [Open in Dropleads ↗](URL) |
```

**Google Search Operators (verify a specific company before outreach):**

```markdown
| What to Check | Google Operator | Positive Result Looks Like |
|---------------|----------------|---------------------------|
| [Signal name] | `site:domain.com "[keyword]"` | [What a positive match means] |
```

**Dropleads URL format — use these parameter names:**

```
People search:
https://app.dropleads.io/#/people
  ?personTitles[]=Title+One
  &personTitles[]=Title+Two
  &personSeniorities[]=vp
  &personSeniorities[]=director
  &personSeniorities[]=c_suite
  &qOrganizationKeywordTags[]=vertical-keyword
  &organizationLocations[]=United+States
  &organizationNumEmployeesRanges[]=201-500
  &page=1

Company search:
https://app.dropleads.io/#/companies
  ?qOrganizationKeywordTags[]=keyword-one
  &qOrganizationKeywordTags[]=keyword-two
  &organizationLocations[]=United+States
  &organizationNumEmployeesRanges[]=201-500
  &page=1
```

Valid headcount ranges: `1-10` `11-20` `21-50` `51-200` `201-500` `501-1000` `1001-5000` `5001-10000` `10001+`

Valid seniorities: `vp` `director` `manager` `c_suite` `owner` `partner` `senior` `entry`

Use `qOrganizationKeywordTags[]` for keyword-based company filtering — this searches company descriptions/tags. Do NOT use hardcoded Dropleads industry tag IDs; use keyword tags instead.

### 1.4 Buyer Persona Quick Reference

One row per key persona. Pull title patterns and pain points from job hiring signals + keyword analysis. Include 3–5 personas covering: primary decision-maker, economic buyer, technical evaluator, champion.

```markdown
| Persona | Title Pattern | Pain Point | Signal to Reference | Dropleads Search |
|---------|--------------|------------|---------------------|---------------|
| [Name] | [Title 1, Title 2, Title 3] | [Core pain point] | [Top signal + lift + where to find it] | [Search ↗](URL) |
```

### 1.5 Lead Scoring Cheatsheet

Condensed scoring model — score any prospect in under 2 minutes.

```markdown
| Signal | Points | How to Check |
|--------|--------|--------------|
| [Top positive signal] | +[N] | `site:domain.com "[keyword]"` OR Dropleads tech/jobs |
| ... (8–12 positive signals total) | | |
| [Top anti-fit signal] | −[N] | [How to check] |
| ... (4–6 anti-fit signals total) | | |
```

Score tiers:

```markdown
| Score | Tier | Action |
|-------|------|--------|
| 60–100 | 🟢 Tier 1 | Immediate — personalized sequence referencing their specific signals |
| 35–59 | 🟡 Tier 2 | Trigger-based — sequence on funding, industry news, or hiring event |
| <35 | 🔴 Tier 3 | Nurture or skip — likely not a fit today |
```

---

## Header

```markdown
# {Company Name} ICP Niche Signals Report

**Analysis Date:** {{date}}
**Target Company:** {{company}} ({{domain}}) — {one-line description}
**Dataset:** {{won_count}} Closed Won + {{lost_count}} Closed Lost accounts
**Data Sources:** Multi-page website extraction (exa_search with contents, ~8 pages/company) + job listings (Crustdata)
**Coverage:** {{won_with_content}}/{{won_count}} won and {{lost_with_content}}/{{lost_count}} lost with website content; {{won_with_jobs}}/{{won_count}} won with job listings
```

---

## Section 2: Executive Summary

**Format:** 2-3 direct sentences profiling best-fit customers. Include top 3 differentiating signals with lift values.

**REQUIRED: Add prospective target companies** (not in dataset) that match the ICP profile:
- List 4-6 concrete companies that fit the profile but aren't current customers
- Include: company name, size, specific signals (hiring roles, tech stack, pain points mentioned)
- Shows what the ICP looks like in the wild

**Example:**
> {{Target}}'s buyers are mid-size companies (100-1000 employees) scaling {{domain}} operations. Top signals: hiring {{domain}}-related roles (3-5x lift), using {niche tools} (2-4x lift), mentioning "{buyer pain point}" (3-6x lift).
>
> **Companies that fit this profile but aren't customers yet:**
> - {Company A} ({{size}} employees) — {specific signal 1}, {specific signal 2}
> - {Company B} ({{size}} employees) — {specific signal 1}, {specific signal 2}

**Avoid:** Generic "perfect fit customer" descriptions. Be specific and concrete.

### Dataset Caveat (if applicable)

If the dataset has limitations, add a caveat subsection. Common caveats:
- Lookalike companies used as Won (they haven't actually purchased — signals are inferred fit, not validated)
- Small sample size (<20 won or <10 lost)
- Uneven group sizes (e.g., 8 won + 32 lost)
- Auto-extracted domains without manual verification

---

## Section 3: Website Keyword Differential

Methodology note at the top:
> Substring matching across multi-page website content for {{won_n}} won and {{lost_n}} lost companies. Lift uses Laplace smoothing: `((won + 0.5) / (won_total + 1)) / ((lost + 0.5) / (lost_total + 1))`. **Bold** = lift > 2x.

### Subsections by category (3.1, 3.2, etc.)

Table format:
```markdown
| Keyword | Won (n=X) | Lost (n=Y) | Lift | Interpretation |
```

**Quality rules:**
- Raw counts always: `15% (6)` not just `15%`
- Sample sizes in headers: `Won (n=37)`, `Lost (n=18)`
- **Bold** lift > 2x only
- Interpretation column required — explains WHY this matters for the target company

### Source Evidence (Required for top 3 keywords per table)

After each table, add a blockquote with **exact quotes** and **linked sources** for the top 3 keywords. The analysis script outputs `evidence` objects with `company`, `source_type`, `quote`, `url`, and `page_title` or `job_title`.

Format evidence as:
```markdown
> **Evidence — "keyword1":**
> - [company1.com](url) (page title): "...exact quote with keyword in context..."
> - [company2.com](url) (job: "Job Title"): "...exact quote from job listing..."
>
> **"keyword2":**
> - [company3.com](url) (page title): "...exact quote..."
```

Each evidence entry must include:
1. **Company domain** as a link to the source URL
2. **Source context** — page title for websites, job title for listings
3. **Exact quote** — the ±40 char snippet around the keyword match from the raw text
4. **Vendor-adjacent annotation** — If the evidence comes from a company that also sells a similar product (e.g., their pricing page mentions the keyword), mark with ⚠️ and note "vendor-adjacent". Clear buyer signals get ✅.

### Sales-Specific Keywords: Source Breakdown

For sales-specific keywords, add a **Source** column showing where matches came from:
```markdown
| Keyword | Won (n=X) | Lost (n=Y) | Lift | Source (website / jobs / both) | Interpretation |
```

Source format: `3w / 20j / 2both` (3 from website only, 20 from job descriptions only, 2 from both)

### Tech Stack Keywords: Niche Tool Mentions

Search for specific SaaS tools (not generic keywords like "cloud" or "security"). Group by category:
- Sales & Revenue Tools
- Data & Analytics Tools
- Customer Success & Support
- HR & ATS
- Anti-Fit Tech Stack

### Anti-Fit Keywords
Separate table for keywords with lift < 0.5x.

---

## Section 4: Structured Signal Categories
GTM motion indicators, infrastructure maturity tables with Won%, Lost%, and interpretation.

---

## Section 5: Job Hiring Signals
Role prevalence in won companies. If lost companies lack job data, present won-only with note.

---

## Section 6: Anti-Fit Signals & Competitive Tool Users

### Anti-Fit Signals Table
Website content anti-signals table for keywords with lift < 0.5x that indicate structural misfit.

### Structural Anti-Fit Patterns
Patterns indicating the company is not a fit:
- Selling the same product category (competitor, not buyer)
- No job listings in 12+ months (not growing/hiring)
- Consumer-focused business model (if target sells B2B)
- Industry/vertical mismatch

### Competitive Tool Users (Migration Opportunity Segment)

**DO NOT exclude companies using competitor tools.** Instead, create a separate prospecting segment:

```markdown
| Company Segment | Count | Approach |
|-----------------|-------|----------|
| Using [Competitor A] | N (X% of lost) | Displacement messaging, comparison content |
| Using [Competitor B] | N (X% of lost) | Migration case studies |
```

### Red Flag Checklist

Deprioritize if 2+ present (excluding competitive tool usage):
- ✅ Selling the same product (competitor)
- ⚠️ No relevant job listings in 12 months
- ⚠️ <50 employees
- ⚠️ Consumer-only business model

---

## Section 7: Composite Lead Scoring Model
0-100 point model organized in 3 tiers:
- Tier 1: Core Fit (0-40 points) — regulatory, compliance, or structural signals
- Tier 2: Sophistication (0-30 points) — fraud/risk/product maturity signals
- Tier 3: Developer / Integration Fit (0-30 points) — API-first, tech stack signals

Include scoring examples from the dataset (2 won, 2 lost with full point breakdown).

**CRITICAL — Scoring reconciliation:** After writing this section, cross-check every signal's point value against Section 1.5 (Lead Scoring Cheatsheet). They MUST match. Mismatches between the quick-reference and detailed sections confuse users.

---

## Section 8: Niche First-Party Signals to Pull
Actionable checklist grouped by priority:
- Highest-value (pull for every prospect)
- High-value (pull for Tier 1-2)
- Enrichment signals (context for personalization)

---

## Section 9: Won vs Lost Comparison
Side-by-side archetype profiles with concrete examples from the dataset.

---

## Section 10: Recommended Prospecting Workflow

4-step targeting guide: Build list → Enrich → Score → Personalize.

### Step 1: Build Target Account List
Concrete ICP filters for Dropleads/LinkedIn:
- Employee count range (derived from won data)
- Industry/vertical tags
- Location filters
- Exclusion criteria (competitor tools, anti-fit industries)

### Step 2: Enrich with First-Party Signals
Checklist of data to pull per account:
- [ ] Job listing signals (specific roles from Section 5)
- [ ] Tech stack signals (specific tools from Section 4)
- [ ] Pain point keywords (from Section 3)
- [ ] Compliance/maturity indicators

**Data sources:** Crustdata (jobs), Exa (website content), LinkedIn (team size), BuiltWith (tech stack)

### Step 3: Score & Prioritize
Apply scoring model from Section 7. Group into tiers with specific action per tier:
- **Tier 1 (80-100):** Immediate — personalized AE outreach, multi-threaded
- **Tier 2 (60-79):** Sequence — automated sequence with manual personalization
- **Tier 3 (40-59):** Nurture — content marketing, webinars, product updates
- **Disqualified (<40):** Do not pursue

### Step 4: Personalize by Signal

**REQUIRED: Include 4-6 persona-specific outreach templates** based on the buyer personas from Section 1.4. Each template should reference a specific signal from the report and connect it to a concrete pain point.

Template format per persona:
```
**[Persona Name] — [Signal Trigger]:**
Subject: [Specific subject line referencing the signal]
Body: "Hi [Name], [observation referencing the signal] — [pain point it creates] — [how target company solves it] — [social proof from dataset]. Worth a 15-min call?"
```

Include personalization hooks for each signal category:
```
• Hiring trigger: "Saw you're hiring a [role] — we work with [comparable company] to help their [team] focus on [outcome] rather than [pain]..."
• Tech stack signal: "Saw [Company] uses [tool] — teams running [tool] often face [specific friction]..."
• Pain point signal: "Noticed [Company] mentioned [pain point] — [comparable company] had the same issue before [solution]..."
• Competitive signal: "You're using [competitor] — [specific reason a switch makes sense right now]..."
• Regulatory/compliance trigger: "Noticed [Company] has [signal] — companies at this maturity typically [pain point]..."
```

### Step 5: Campaign Execution

**Outreach channels by tier:**
- **Tier 1:** Personalized email from AE + LinkedIn InMail to decision-maker
- **Tier 2:** Automated sequence with SDR follow-up
- **Tier 3:** Marketing automation (email drip + retargeting)

**Messaging pillars** (3-4 pillars derived from top signals):
1. [Top pain point signal] → "[One-line messaging hook]"
2. [Top hiring signal] → "[One-line messaging hook]"
3. [Top tech stack signal] → "[One-line messaging hook]"
4. [Social proof] → "[Customer name] + [result]"
