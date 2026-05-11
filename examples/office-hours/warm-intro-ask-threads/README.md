# Warm intro ask threads

Office-hours example — the step after scoring. You have your ranked connectors from `../warm-intro-scoring/`. Now you need to actually ask.

This generates personalized ask messages for each connector, grounded in the shared signal that gave them their score, then optionally sends them via LinkedIn or formats them for copy-paste.

## Prerequisites

Run the warm-intro-scoring example first. You need a scored connector list (output of `lookup.py`). See [`../warm-intro-scoring/`](../warm-intro-scoring/) for the full setup.

## What this does

1. Takes the top-N results from `lookup.py` — exported as CSV.
2. For each connector, selects the primary shared signal: company overlap or role similarity.
3. Calls the Deepline API to draft a message under 80 words, with the ask in the first line.
4. Outputs a CSV of draft messages ready for review.
5. Optionally sends via LinkedIn (Apify) with rate limiting and a send log.

## Input

The scored connector CSV from `lookup.py`. Expected columns:

| Column | Source |
|---|---|
| `connector_name` | Contact full name |
| `connector_linkedin` | Contact LinkedIn URL |
| `connector_company` | Contact current company |
| `target_name` | The person you want an intro to |
| `target_company` | Their company |
| `shared_signal` | `company_match` or `role_overlap` |
| `shared_detail` | e.g. `"Stripe"` or `"Head of Growth"` |
| `score` | Numeric score from scorer.py |

Export this manually from `lookup.py` output or pipe it using the `--csv` flag (not yet implemented in lookup.py — add it yourself if needed).

## Output

`ask_drafts.csv` — one row per connector:

| Column | Description |
|---|---|
| `connector_name` | Connector's full name |
| `connector_linkedin` | Connector's LinkedIn URL |
| `target_name` | Person you want introduced to |
| `shared_signal` | Signal type driving the ask |
| `draft_subject` | Short subject line (for email fallback) |
| `draft_body` | The message body — ready to send or lightly edit |
| `score` | Original score from scorer.py |

## Ask anatomy

Every draft follows the same structure:

1. **Line 1: the ask.** Specific, direct. "Would you be willing to intro me to [name]?" No wind-up.
2. **Line 2: the reason.** Why you're asking *this* connector. References the shared signal — "You both worked at Stripe" or "You're both building in the growth eng space."
3. **Line 3: one sentence on why it matters.** What you need the intro for. No "hop on a call to explore synergies." Concrete.

Things the prompt explicitly bans: "pick your brain", "hope this finds you well", "I'd love to connect", "quick chat". If the model adds any of these, re-run.

## Files

- `draft_asks.py` — loads scored CSV, calls Deepline API to generate message drafts, writes `ask_drafts.csv`.
- `send_via_linkedin.py` — takes `ask_drafts.csv`, sends each message via Apify LinkedIn actor. Has `--dry-run` and `--limit` guards. Logs every send to `send_log.db`.

## Usage

```bash
# 1. Draft messages for your top connectors
export DEEPLINE_API_KEY=your_key
python draft_asks.py --input scored_connectors.csv --output ask_drafts.csv --top 20

# 2. Review ask_drafts.csv — edit any message you want to change before sending

# 3. Dry-run to see exactly what would go out
python send_via_linkedin.py --input ask_drafts.csv --dry-run

# 4. Send (default cap: 5 per run)
python send_via_linkedin.py --input ask_drafts.csv --limit 5

# Increase limit cautiously — LinkedIn ToS risk rises sharply above 10/day
python send_via_linkedin.py --input ask_drafts.csv --limit 10
```

## Cost

- Deepline message drafting: ~$0.002 per message (Claude Haiku via Deepline API)
- Apify LinkedIn send: ~$0.02–0.05 per send depending on actor pricing
- 20 connectors: under $1 total

## What this doesn't do

It does not know if your connector will actually respond. A score of 90 and a good message still requires the connector to like you enough to forward. Review each draft before sending — the model doesn't know your actual relationship with each person.
