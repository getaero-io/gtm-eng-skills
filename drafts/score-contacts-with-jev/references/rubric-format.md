# The rubric file

One JSON object. `scripts/rubric_tool.py check <file>` validates it and prints the card the
installer reads; `save` stores it for the workspace and bumps its version when the content changed.
`scripts/rubric.example.json` is a complete, invented example.

## Top level

| Key | | |
|---|---|---|
| `entity` | required | `account` for the account skill, `contact` for the contact skill. A rubric for the other one is refused |
| `name` | required | shown on every result as `name vN` |
| `about` | recommended | `we_sell`, `ideal_customer` (or `buyer` for contacts), `sources`: where each part came from (memory, a doc, the interview). Not sent to Jev |
| `inputs` | required | the fields a record carries, below |
| `rules` | | numbers, dates and lists, worked out in code. Free |
| `questions` | | judgments, asked of Jev. One request per record for all of them |
| `tiers` | default A≥70, B≥45, C≥25, D≥0 | `[{"tier": "A", "min": 70}, …]`; the lowest must start at 0; a status word cannot be a tier name |
| `tiers_origin` | optional | `"default"` when the installer accepted the proposed cut-offs rather than choosing them |
| `confidence_floor` | default 0.6 | answers below it go in `needs_review` |
| `min_coverage` | default 0.5 | below it the tier is `insufficient_data` |

Any rule or question may carry `"origin": "default"` when the installer accepted a proposed value
rather than choosing it, and `"tiers_origin": "default"` does the same for the cut-offs. The card
then lists them as borrowed, and so should the delivery.

## `inputs`

```json
{"description": {"label": "What the company does", "type": "text", "max_chars": 3000}}
```

Keys are lower_snake_case and become the play's input names (what a CSV's columns are mapped
onto; a webhook body uses them as they are). `type` is `text` (default), `number` or `date`. `required: true` means a record without it is
`not_scored` and Jev is not called. Text longer than `max_chars` (default 4000) is cut before
sending, which bounds the cost of a record with a huge scraped page in it. `source_ref` is
reserved: it is echoed back for joining.

## `rules`: never sent to Jev

| `kind` | Reads | Shape |
|---|---|---|
| `bands` | a number (`1,200`, `51-200` → midpoint, `10k`, `2.5M`) | `bands`: `[{"below": 50, "points": 0, "says": "under 50 staff"}, …, {"points": 5, "says": "2,000+"}]`, increasing `below`; the last may leave `below` out |
| `days_since` | a date `YYYY-MM-DD` (or `YYYY-MM`, `YYYY`) | the same `bands`, in days |
| `match` | text, lower-cased, `https://`/`www.` stripped | `values` list, `mode` `equals` or `contains`, `points` / `miss_points`, `says` / `miss_says`; `"disqualify": true` makes a match disqualify (and Jev is then never called) |
| `lookup` | text, matched exactly (case-insensitive) | `table`: `{"a": {"points": 25, "says": "tier A account"}, "b": 15}`, `miss_points` / `miss_says` for anything else. How a contact inherits its account's tier |
| `present` | anything | `points` when the field has a value |

A blank or unreadable input gives the rule no points and counts against coverage; it never counts as
a "no".

## `questions`: sent to Jev

Every question has `id`, `label`, `kind` (`noul`, `choice`, `score`), `reads` (the inputs it needs:
a question whose inputs are all blank is not sent) and `instructions` (the question, with fields
named in backticks). Then, by kind:

- **noul** (sent to `ai_evaluate` as type `boolean`): `criteria` `{"true": "what yes means", "false": "what no means"}`, `points`
  `{"yes": 20, "no": 0}`, `says_yes` / `says_no`, optional `disqualify_at` (0.5 to 1: a yes at or
  above it disqualifies).
- **choice**: `options`
  `{"key": {"means": "…", "points": 25, "says": "a distributor", "disqualify": false}}`.
  **`not_enough_information` (0 points) is added unless you define it**, and an answer landing there
  counts against coverage rather than as a verdict. An option marked `disqualify` disqualifies when
  its probability reaches `disqualify_at` (default 0.8).
- **score**: `levels`, 2 to 10, lowest first; `points` for the top level. Points are
  `score ÷ (levels − 1) × points`. Level 0 is the bottom of the scale: "no evidence" for a signal,
  the most junior for seniority.

## How a record's score is worked out

1. Each rule and question earns points. A question earns its **expected** points over Jev's
   probabilities (a 25-point option at 60% gives 15), so doubt lowers a score instead of flipping
   it.
2. Score = earned ÷ the most any record could earn × 100, clamped to 0–100, rounded. Missing data
   earns nothing, so a thin record cannot look strong.
3. Coverage = the points that could actually be judged ÷ the most possible. Below `min_coverage`:
   `insufficient_data`.
4. Status, first match wins: required input missing → `not_scored`; Jev call failed → `failed`; any
   disqualifier → `disqualified`; low coverage → `insufficient_data`; otherwise `scored` with the
   first tier whose `min` the score reaches.

Five statuses, no sixth: `scored`, `disqualified`, `insufficient_data`, `not_scored`, `failed`.

The reasons list up to four criteria that counted **for** the record, shown as "(+25)", then up to
three that counted **against** it, shown as "(2 of 25)". A criterion counts for the record when the
answer Jev chose is itself worth at least half its points; otherwise it counts against, even if
Jev's doubt earned it a few points, so a "no" never reads as a win.

## Writing questions Jev answers well

- One condition per question. "Is it a B2B company that runs a fleet?" is two Nouls.
- Describe every option, including where the boundary is. Jev reads literally.
- Keep numbers out of questions. "More than 200 employees?" is a rule.
- Phrase a Noul so yes means the same thing as `criteria.true`. Contradictions cost accuracy.
- Give each question only the fields it needs in `reads`.
- Prefer a Choice with described options over several overlapping Nouls when the answers are
  mutually exclusive.
