# Source adapters and evidence input

## Existing implementations

- [Office-hours scorer, ingestion, SQLite and Apify enrichment](https://github.com/getaero-io/gtm-eng-skills/tree/main/examples/office-hours/warm-intro-scoring): `ingest.py` loads Connections CSV, `enrich.py` supplies profile URLs to its configured Apify actor, polls the run/dataset, and writes employment/education into SQLite. It requires `requests` for live enrichment, `APIFY_TOKEN`, and the actor's current input/output contract. Review `--limit 1 --batch-size 1` first. Ingestion assigns UUIDs; do not reimport the same export without a dedup policy.
- [Ask threads](https://github.com/getaero-io/gtm-eng-skills/tree/main/examples/office-hours/warm-intro-ask-threads): compatible CSV input and explicit draft/send gates. The scorer wrapper imports from this repository's existing sibling examples; installed copies of the skill still require `--repo` pointing to a checkout.
- [Target-account orchestrator](https://github.com/getaero-io/gtm-eng-skills/tree/main/examples/office-hours/target-account-warm-intro-campaign): account qualification, stable identities, provider policy and activation ledger. Its 60/30/15/7/3 score scale is not the 160/80 office-hours scale.
- [Event workflows](https://github.com/jptoor/event-network/tree/main/workflows): HarvestAPI profile/history pulls, Hunter fallback, Deeplineagent research, Jev batch/recovery/live callback, and Luma ingestion. `jev.ts` and `scoring-model.ts` define prompts and validation. Jev uses `ai_evaluate` with `typesafe-ai/jev`; structured extraction is followed by deterministic pair comparison. Do not claim this repo contains an Apify connection-list collector.
- [Event scoring](https://github.com/jptoor/event-network/blob/main/docs/SCORING.md): use the existing pair APIs for room matching. The gift/product-fit score is not a relationship score. Luma registration and physical check-in remain distinct and neither implies opt-in.

Read source contracts from your checked-out revision before live execution. Record revision IDs with each evaluation. Initial wrapper parity was checked against GTM Eng Skills `7223771` and the event source release `a17fd35`.

## Batch collection first

Follow the [batch collection contract](batch-collection.md) for all bulk work. The single-profile examples below are schema and identity checks, not the production loop. Reuse caches, batch unresolved URLs, bound concurrency and retain pending job receipts before fallback.

## Bounded Deepline profile pilot

Setup: [Deepline CLI](https://code.deepline.com). Inspect the tool schema in the active workspace before executing. The native single-profile tool accepts a `url` input:

```bash
deepline tools execute harvestapi_get_profile --input '{"url":"https://www.linkedin.com/in/REVIEWED_PROFILE"}'
```

Replace the example with a verified authorized profile URL. When using `deepline enrich` on a CSV, apply `--rows 0:1` to your configured command first, verify output identity and history fields, then expand only within the approved row/spend limit. Do not execute the placeholder or assume a connection exists because the profile resolves. For Apify use the example's explicit `--limit 1 --batch-size 1`; `--rows` is a Deepline batch flag, not an Apify flag. Cache attributable results; uncertain paid-call outcomes require reconciliation before retry.

## Reviewed JSON for score.py

`assets/example.json` is a complete fictional runnable input. Top level:

| Field | Meaning |
|---|---|
| `campaign_id`, `owner_id` | Required stable namespaces; owner must differ from connector and target. |
| `as_of` | Required ISO date; freezes scoring and excludes later-observed evidence. |
| `evidence` | Required registry of ID, kind, subjects, detail, source locator, observed_at. |
| `paths` | Reviewed candidate pairs with records below. |

Each path has required `connector` and `target` objects: `id`, `first_name`, `last_name`, `linkedin_url`; optional `current_company`, `current_position`. Profile URLs identify profiles only. Optional `connector_experiences` and `target_experiences` contain `id` (also registry evidence ID), `contact_id`, `company_name`, ISO `start_date`/`end_date` or null, and boolean `is_current`. Unknown dates stay null. Only current roles may use `as_of` as an open end. Partial/year-only dates must not be silently expanded to claim precise overlap; retain uncertainty or route to review.

Optional fields:

- `relationship_confidence`: unknown/low/medium/high/confirmed, with `relationship_evidence_ids` citing kind `relationship`, matching reviewed `confidence`, and both owner/connector subjects.
- `target_relationship_confidence` and `target_relationship_evidence_ids`: same labels, subjects connector/target.
- `direct_intro_evidence_ids`: kind `direct_intro`, subjects connector/target. Must describe an actual supported introduction, not a draft request or model guess.
- `connector_willingness`: unknown/yes/no, with `willingness_evidence_ids`, kind `willingness`, explicit `value` of yes/no, subjects owner/connector/target. The latest relevant dated record governs; a same-day conflict or newer decline blocks even when the path cites an older yes. A prior unrelated yes is insufficient.
- `signals`: `{kind,value,evidence_ids}`. Kinds school, city, community, appearance, role_industry, investor. Each evidence row must include both connector/target IDs and matching kind. Evidence supports the particular shared fact, not merely two vaguely relevant pages.

The script validates IDs, chronology, subject/kind linkage and numeric output. It cannot establish that a citation's prose is true; human/source review remains necessary. Registry source locators can be private record IDs. The public-facing artifact exposes citation IDs, not raw messages or emails. Store the registry privately next to the artifact for review.

CSV adds `model_version`, `baseline_segment`, `target_relationship_confidence`, `connector_willingness`, and `review_status` to the existing ask schema. Extra columns are accepted by its loader. A high factual score may remain held. `reviewed_override` is always false.

## Account-domain holds and export coverage

An `account_domain_mismatch` remains unresolved until stable-identity evidence supports the account assignment. Do not copy the requested domain onto a profile with a different employer to make scoring pass. Restore missing assignment metadata only from an attributable collection request. Accept a domain alias only with sourced company equivalence. Record the reason and source of each correction. Rerun feature extraction and preserve declines and holds. Keep unresolved targets visible even when they have no scored path.

If export completeness is not verified, supply the original source manifest to `plays/merge-payloads.py --source-input` and reconcile the expected target keys. `target_exports_verified` confirms target export coverage only; it does not prove full employee collection or profile accuracy. Keep source-run coverage separate from later user-reported gaps. Never merge either report by name alone.

A mismatch compares the target account domain with the exact matched profile's assigned domain, not the requester's email domain. Coverage includes `domain_check.status`, `expected_domain`, `profile_domain`, `profile_id`, `source` and `observed_at`. Missing profile metadata, missing target metadata and different domains remain distinct diagnostics under the same hold. The report shows the title from the target record, or the exact matched profile if absent; it never uses a name-only title match.
