# RSVP Scoring Framework

## Segment definitions

| Segment | Definition | Action |
| --- | --- | --- |
| `hot` | ICP company + ICP title + LinkedIn verified | Approve immediately; flag for host |
| `warm` | ICP company OR ICP title | Approve if capacity allows |
| `low` | Email valid, but no ICP match | Waitlist or decline |
| `skip` | Invalid email, agency, competitor, or spam pattern | Decline |

## ICP matching

### Company signals (AND logic recommended)

- In TAL (target account list)
- Employee range: {{your_icp_employee_range}}
- Industry: {{your_icp_industries}}
- Funding stage: {{your_icp_funding}}
- Tech stack: {{your_icp_tech_signals}}

### Title signals (OR logic typical)

- Exact match: VP Sales, CRO, Head of Growth, VP Revenue, etc.
- Seniority: Director+ in GTM function
- Function: Sales, RevOps, Growth, Partnerships

### LinkedIn verification

- Profile found and matches name + company
- Currently employed at stated company (not stale data)
- Profile is public and active

## Scoring edge cases

| Case | Segment | Notes |
| --- | --- | --- |
| Founder at early-stage startup | `warm` or `hot` | Depends on TAL fit |
| Agency email or consultant | `skip` | Unless explicitly invited |
| Investor at relevant fund | `hot` | Portfolio access is valuable |
| Student or recent grad | `low` or `skip` | Unless program is open to students |
| Competitor | `skip` | Clearly mark and decline |
| Generic/role email (info@, hello@) | `skip` | Not a person |

## Capacity approval logic

1. Count current `approved` + `checked_in`
2. Count `hot` in pending/waitlist
3. If `approved + hot` ≤ capacity: approve all `hot`
4. If `approved + hot` > capacity: rank `hot` by TAL priority, seniority, registration timestamp
5. Fill remaining slots with `warm` using same ranking
6. Move rest to waitlist with note

## Host-hit shortlist

From `hot` segment, rank by:

1. TAL priority (if applicable)
2. Seniority / title prestige
3. Warm intro potential (shared connections, prior engagement)

Flag top 20–40 for host prep. Include:
- Name, title, company
- LinkedIn URL
- Why they matter (ICP fit, TAL, influence)
- Suggested intro angle or talk track
