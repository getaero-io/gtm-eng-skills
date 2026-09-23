---
name: warm-intro-scoring
description: |
  Rank evidence-backed requester → connector → target introduction paths, or match event attendees by shared professional context. Produce an interactive local review artifact with the top three paths, score explanations, and evidence. Use for warm-intro scoring, connector selection, relationship mapping, and event match recommendations. Keeps similarity separate from relationship proof and ask approval.
---

# Warm intro scoring

Produce a ranked review artifact, a machine-readable scored-path CSV, and an honest evaluation summary. Reuse the existing scorers; do not invent a new weighted model for each run. No messages are sent by this skill.

## Choose the scoring question

- **Find a connector to a named person:** requester → connector → target. Both relationships matter. Use the target-person office-hours scorer through `scripts/score.py`.
- **Find contacts by company/school criteria:** use the existing `lookup.py` discovery interface. Company proximity is not dated overlap. Do not present its score as target-person evidence.
- **Match people in a room:** use the event app's pair scorer (function 35%, previous roles 25%, school 15%, industry 15%, employers 10%). Keep missing dimensions unknown rather than redistributing their weight. Pair similarity is separate from warm-intro strength, product fit, and gifts. See [source adapters](references/sources.md).

Ask only for missing essentials: requester identity, target person/list or event cohort, intended reason for meeting, permitted data sources and budget. Reuse the user's existing approved scope. Default to private local artifacts and no live enrichment when cached evidence suffices.

## Gather and normalize evidence

Read [sources and input contract](references/sources.md). Reuse an owner-scoped LinkedIn Connections export or existing relationship database. Apify enriches supplied profile URLs; it does not magically retrieve all connections. Preserve connection-export provenance separately from profile enrichment. A profile URL, shared investor, event registration, or co-employment alone never proves a relationship.

Use stable IDs for requester, connector, target, employer and evidence. Hold ambiguous names and conflicting identities. Preserve source locator, evidence kind, subjects, observed date, actual interaction/employment dates, and a short supported detail. Only use information available as of the scoring date. Never invent jobs/dates to explain a known successful introduction.

For paid enrichment, validate the selected tool schema and do a one-row pilot (`--rows 0:1`) before a reviewed bounded batch. See the executable Deepline example in [sources](references/sources.md). Keep tokens, raw profiles, messages, connection lists and real-person artifacts outside Git. Credentials do not imply consent to send messages or publish people.

## Score and review

The wrapper requires a GTM Eng Skills checkout; it imports the maintained example scorer rather than shipping another copy. Set `GTM_REPO` to that checkout and `SKILL_DIR` to this skill directory. Install requires Python 3.10+; scoring/rendering use only the standard library.

```bash
python3 "$SKILL_DIR/scripts/score.py" reviewed-evidence.json \
  --repo "$GTM_REPO" --output scored-paths.csv
python3 "$SKILL_DIR/scripts/render.py" scored-paths.csv --output intro-review.html
```

Outputs refuse overwrite and are created with private permissions. Select a new output filename per run. The reference fixture is `assets/example.json`; use it only for demonstration.

The pinned baseline uses direct-introduction evidence 160, dated work overlap 80, owner relationship 0/5/10/15, school/city/community 40, role/industry 20, investor context capped at 3. These are ordinal evidence points, not percentages or success probabilities. Keep `model_version` and baseline segment in exports. The campaign example and event app use different scales; never mix their numeric scores.

**Separate score from permission and confidence.** The wrapper holds a nominally strong path for review unless both relationships have at least medium cited confidence and the connector has documented willingness for this particular introduction. A decline blocks the path while retaining the factual score. Even a ready-for-human-review path is not approved or sent. Unknown willingness stays unknown. A historic introduction is not current willingness. Recheck stale/conflicting evidence before proposing an ask.

Read [factor research](references/factors.md) when extending the model. New signals are hypotheses until evaluated. Keep weak affinities as context or tie-break candidates; do not let many weak facts overwhelm stronger evidence. Exclude sensitive-trait inference and hidden/private social data. Same city, college, sports team, professional club or public social exchange can suggest a conversation, not familiarity.

## Deliver the artifact

Open the generated HTML locally when possible. It must show target and connector identities, requester path, top three alternatives, component scores, evidence IDs, both-edge confidence, willingness and reasons to hold. Include search/status filters, an empty state and responsive keyboard-accessible controls. `scripts/render.py` supplies this without a server or dependencies. The HTML contains the selected people; do not publicly host it without authorization.

The ask preview is illustrative only. Export CSV matches the existing ask-thread loader; keep `reviewed_override=false`. If draft generation is requested, use the existing ask drafter with its segment/row gates and retain `approved=false`. Sending is a separate authorized action. Do not copy raw private evidence into an outbound ask.

## Evaluate before claiming improvement

Run `python3 "$SKILL_DIR/scripts/check.py" --repo "$GTM_REPO"`. Check real ask compatibility without generating or sending asks. [Evaluation](references/evaluation.md) explains the historical audit and regression cases.

For predictive evaluation, require a private dated outcome set: candidate paths available at ask time, connector confirmation/decline, intro sent, target reply, meeting completed, and censored/unknown outcomes. Hold out time and target/account groups. Compare on the same candidate universe; report recall@3/MRR only with relevant-route labels, and reply/meeting rates only with comparable observed sends. Unsent drafts are not failures. Do not fit new weights to hand-selected anecdotes or quote a success rate from structural tests.

Finish with the artifact and CSV paths, scoring version, checks run, real-data coverage and any missing evidence. If the requested reference artifact is inaccessible, say so; do not claim visual parity.
