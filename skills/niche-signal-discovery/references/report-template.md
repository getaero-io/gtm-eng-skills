# Report Template Reference

Template for the niche signals report. Follow this structure and quality rules strictly.

## Header

```markdown
# {Company Name} ICP Niche Signals Report

**Analysis Date:** {date}
**Target Company:** {company} ({domain}) — {one-line description}
**Dataset:** {won_count} Closed Won + {lost_count} Closed Lost accounts
**Data Sources:** Multi-page website extraction (exa_search with contents, ~8 pages/company) + job listings (Crustdata)
**Coverage:** {won_with_content}/{won_count} won and {lost_with_content}/{lost_count} lost with website content; {won_with_jobs}/{won_count} won with job listings
```

## Section 1: Executive Summary

**Format:** 2-3 direct sentences profiling best-fit customers. Include top 3 differentiating signals with lift values.

**REQUIRED: Add prospective target companies** (not in dataset) that match the ICP profile:
- List 4-6 concrete companies that fit the profile but aren't current customers
- Include: company name, size, specific signals (hiring roles, tech stack, pain points mentioned)
- Shows what the ICP looks like in the wild

**Example:**
> Air Inc's buyers are mid-size companies (100-1000 employees) scaling creative operations. Top signals: hiring Creative Operations roles (3.8x lift), using Figma + Adobe CC (3.2x lift), mentioning "fragmented tools" (5.2x lift).
>
> **Companies that fit this profile but aren't customers yet:**
> - Canva (2100 employees) — Design team of 300+, hiring Creative Ops Manager in Sydney, uses Figma + Adobe internally
> - Notion (450 employees) — Content team scaling rapidly, 8 open creative roles, mentions "content discovery" challenges

**Avoid:** Generic "perfect fit customer" descriptions. Be specific and concrete.

## Section 2: Website Keyword Differential

Methodology note at the top:
> Substring matching across multi-page website content for {won_n} won and {lost_n} lost companies. Lift uses Laplace smoothing: `((won + 0.5) / (won_total + 1)) / ((lost + 0.5) / (lost_total + 1))`.

### Subsections by category (2.1, 2.2, etc.)

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

### Sales-Specific Keywords: Source Breakdown

For sales-specific keywords, add a **Source** column showing where matches came from:
```markdown
| Keyword | Won (n=X) | Lost (n=Y) | Lift | Source (website / jobs / both) | Interpretation |
```

Source format: `3w / 20j / 2both` (3 from website only, 20 from job descriptions only, 2 from both)

Include evidence with exact quotes and links for the top 3 keywords, same format as above.

### Tech Stack Keywords: Niche Tool Mentions

Search for specific SaaS tools (not generic keywords like "cloud" or "security"). Group by category:
- Sales & Revenue Tools
- Data & Analytics Tools
- Customer Success & Support
- HR & ATS
- Anti-Fit Tech Stack

### Anti-Fit Keywords
Separate table for keywords with lift < 0.5x.

## Section 3: Structured Signal Categories
GTM motion indicators, infrastructure maturity tables with Won%, Lost%, and interpretation.

## Section 4: Job Hiring Signals
Role prevalence in won companies. If lost companies lack job data, present won-only with note.

## Section 5: Anti-Fit Signals & Competitive Tool Users

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

**Format:**

```markdown
### Currently Using Competitive Tools

Companies using [Competitor A/B/C] represent a migration/replacement opportunity:

| Company Segment | Count | Approach |
|-----------------|-------|----------|
| Using Bynder | 3 (15% of lost) | Displacement messaging, comparison |
| Using Widen/Acquia | 2 (10% of lost) | Migration case studies |
| Using Brandfolder | 1 (5% of lost) | Feature gaps, pricing arbitrage |

**Targeting strategy:**

- Lower priority than greenfield accounts (focus on net-new first)
- Requires different messaging: displacement vs. new adoption
- Look for signals of dissatisfaction (job listings for "improve existing DAM", recent negative reviews)
- Use customer migration case studies if available
```

### Red Flag Checklist

Deprioritize if 2+ present (excluding competitive tool usage):

- ✅ Selling the same product (competitor)
- ⚠️ No creative/marketing job listings in 12 months
- ⚠️ <50 employees
- ⚠️ Consumer-only business model

## Section 6: Composite Lead Scoring Model
0-100 point model organized in 3 tiers:
- Tier 1: Sales Infrastructure (0-40 points)
- Tier 2: Company Fit (0-30 points)
- Tier 3: Engagement Readiness (0-30 points)

Include scoring examples from the dataset (2 won, 2 lost).

## Section 7: Niche First-Party Signals to Pull
Actionable checklist grouped by priority:
- Highest-value (pull for every prospect)
- High-value (pull for Tier 1-2)
- Enrichment signals (context for personalization)

## Section 8: Won vs Lost Comparison
Side-by-side archetype profiles with concrete examples.

## Section 9: Recommended Prospecting Workflow
4-step targeting guide: Build list → Enrich → Score → Personalize.
