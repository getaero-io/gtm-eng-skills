# Signal Interpretation Rules

Rules for correctly interpreting whether a signal indicates a buyer, competitor, or neutral company.

## Rule 1: Seller vs Buyer Distinction

If a company's **website content** mentions terms describing what the target product sells, they're likely a **competitor or adjacent vendor**, NOT a buyer.

**Example:** For an AR automation tool, a company whose website says "our collections automation platform" is a seller/competitor. A company whose job listing says "seeking AR Manager to reduce DSO" is a buyer.

**Application:** When a keyword has high lift but companies mentioning it are vendors in the target's space, flag it as a competitor signal, not a buying signal.

## Rule 2: Job Listings = Highest Intent

Hiring for roles related to the target's domain = very high buying signal:

- They have the pain point (they need the role)
- They are actively investing to solve it (budget allocated)
- They may not know automation exists (hiring humans instead)

**Application:** Weight job listing signals higher than website content signals. A company hiring 3 AEs is a stronger signal than a company with "sales" on their website.

## Rule 3: Tech Stack Correlation

Not all tech signals are equal. Consider whether the technology **correlates** with or is **inversely correlated** to the target's use case:

- **Positive correlation:** Technologies that create MORE complexity the target solves (ERP, CRM, payment processors for AR tools)
- **Inverse correlation:** Technologies that SOLVE the problem already (Shopify for AR tools — consumer payments are immediate, not invoiced)

## Rule 4: Source Context Matters

Same keyword means different things depending on WHERE it appears:
- **Product/features page:** Company SELLS this capability → competitor signal
- **Careers/jobs page:** Company NEEDS this capability → buyer signal
- **Blog/case study:** Could be either — evaluate if they're writing as vendor or sharing operational experience
- **Integrations page:** They connect to relevant systems → infrastructure signal

## Rule 5: n=1 Signals Need Verification

A signal appearing in only 1 won company with 0 lost companies produces mathematically high lift but is statistically unreliable. From actual runs:
- n=1 signals with 10x lift scored higher than n=4 signals with 3x lift under the original formula
- After correction: weight n=1 signals at 0.3x, n=2 at 0.6x, n=3+ at 1.0x

**Application:** Flag n=1 signals in reports with "*(single company — verify)*". Never use n=1 signals as Tier 1 scoring criteria.

## Rule 6: Website Signals Fail for Back-Office Tools

For B2B infrastructure tools (AR automation, billing, compliance, HR), buyers don't publish their pain on public websites. From actual analyses:
- 0 of 7 verified customers had AR-related website signals
- All "accounts receivable" signals came from false positives (vendors, not buyers)
- Verified customers (e.g., wholesale distributors, manufacturers, enterprise brands) talk about their own products, not back-office operations

**Application:** For back-office tool verticals, deprioritize website keyword signals. Instead rely on:
1. Job listings (hiring AR Manager, Collections Specialist = active pain + budget)
2. Tech stack signals (NetSuite, Salesforce, Stripe in job descriptions)
3. Business model indicators (B2B invoicing, wholesale distribution)
4. Firmographics (industry vertical, company size, revenue model)

## Rule 7: Anti-Fit Signals Are as Valuable as Fit Signals

From actual analyses: 80% of lost companies were disqualifiable using just 3 anti-fit signals (shopper, checkout, cancel). Identifying non-buyers early prevents wasted outreach.

**Application:** Always generate a dedicated anti-fit section. Key anti-fit patterns:
- Consumer signals (shopper, checkout, cart, debit card) → B2C, not B2B
- Retention/churn language → consumer subscription, not enterprise
- Product category language on product pages → competitor, not buyer
- No job listings → not growing, no budget

## Applying These Rules in Reports

When writing the interpretation column:
1. State what the signal indicates about the prospect's operations
2. Explain WHY it matters for the specific target company
3. Flag ambiguous signals (e.g., "Note: some companies mention this as vendors, not buyers")
4. For ALL keywords, note whether the source is primarily website or job descriptions — job-sourced signals are higher confidence
5. For tech stack tools, explain what the tool usage implies about the org's maturity and needs
6. For n=1 signals, add verification note
7. For back-office tool verticals, explicitly call out when website signals are unreliable and recommend alternative signal sources
