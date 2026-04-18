# Hierarchy Inference Rules

## Seniority classification (internal, 13 levels)

| Rank | Level | Patterns (check in order, first match wins) |
|------|-------|---------------------------------------------|
| 0 | ceo | "ceo", "chief executive" |
| 1 | c-level | "chief" + any (cto, cfo, coo, cmo, cro, cpo, cao, cio) |
| 2 | evp | "evp", "executive vice president" |
| 3 | svp | "svp", "senior vice president" |
| 4 | vp | "vice president", word-boundary "vp", "area vice president", "avp" |
| 5 | sr-director | "senior director" |
| 6 | director | "head of", "head,", "director" |
| 7 | sr-manager | "senior manager", "group product manager" |
| 8 | manager | "manager" |
| 9 | principal | "principal", "staff" |
| 10 | lead | "lead" |
| 11 | senior | "senior", "sr." |
| 12 | ic | everything else |

## Display seniority (for UI, 4 levels)

For rendering in the org chart, simplify to 4 visual levels:

| Display | Internal levels | Color |
|---------|-----------------|-------|
| exec | ceo, c-level, evp, svp, vp | #a78bfa |
| director | sr-director, director | #60a5fa |
| manager | sr-manager, manager, principal, lead | #34d399 |
| ic | senior, ic | #525252 |

## Manager prediction scoring

```
score = seniority_gap + team_match + geo + experience_delta
```

| Factor | Condition | Score |
|--------|-----------|-------|
| Seniority gap | Exactly 1 level above | +10 |
| Seniority gap | 2 levels above | +5 |
| Seniority gap | 3 levels above | +2 |
| Seniority gap | 4+ levels | +1 |
| Seniority gap | Same or below | Skip |
| Team match | Same team | +8 |
| Team match | Related (substring) | +3 |
| Geo | Same city | +2 |
| Geo | Same country | +1 |
| Experience | 3+ more years | +2 |
| Experience | 8+ more years | +3 (replaces +2) |

Highest score wins. Min threshold: 5.

## Peers

Same seniority rank, excluding self.

## Direct reports

1-2 levels below target. Prefer same team. Gap of 1 with no team info still counts.

## Team from title

"Director of Engineering, Identity" -> team = "Identity" (text after comma).
Filter out: Sr, Jr, II, III, Senior, Junior, Lead, Staff, Principal.

## Confidence

3+ sources: high. 2: medium. 1: low.

## Building the hierarchy

1. Find target's most likely manager (highest scoring candidate)
2. Walk upward: find manager's manager, repeat until no senior candidate or score < 5
3. Topmost person = root
4. Find target's peers (same seniority)
5. Find target's direct reports (1-2 below, same team preferred)
6. Peers go under same manager as target
7. Build edges: parent -> [children]
8. Prune unconnected nodes

## Team consolidation

When original data has >8 teams, consolidate into 5-6 groups:

| Original | Simplified |
|----------|------------|
| Executive Leadership, Office of CEO | Leadership |
| Sales, GTM, Business Development | Sales |
| Revenue Operations, Sales Operations, GTM Ops | Revenue Ops |
| Sales Enablement, Enablement | Enablement |
| GTM Strategy, Strategy | Strategy |
| Marketing, Demand Gen, Product Marketing | Marketing |
| Customer Success, Support | Customer Success |
| AI, Product, Engineering, Data, Analytics | Product & Eng |
| HR, People, Finance, Legal | Other |
