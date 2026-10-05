# Alpha Copy evidence and output contract

## Inputs and personalization

Every manual trigger input is a string. Offer and ICP are plain English. Optional
`settings_json`, `evidence_json` and advanced `sender_offer_json` are JSON-encoded strings.
The preferred path is Offer + optional ICP + sender/signature, not advanced JSON.
At least Offer or ICP and a company domain are required. ICP-only mode performs research
but returns missing-offer instructions instead of copy. Greeting, signature and CTA support
only `{{first_name}}`, `{{company_name}}`, `{{sender_name}}`. Missing token values hold output;
unknown/malformed tokens are rejected. No greeting is generated when Greeting is blank.
Blank Signature uses Sender name. Blank CTA lets the workflow propose one question. A supplied
CTA is preserved verbatim, including a statement with no question mark or an intentional
booking URL. Generated URLs are blocked; user-supplied links are allowed.

The writer returns subject, observation, implication and CTA separately. Code
assembles greeting + observation + implication + the exact supplied offer + CTA + signature.
The writer cannot change the actual offer, contact name or signature. Any unexpected
generated offer field is ignored. The critique evaluates that exact assembled offer, not
an imagined model-written offer. Enter the Offer as a complete sentence ready for the email. Copy checks apply to generated lines and CTA, while supplied signature
text stays exact. All words, including greeting/signature, count toward the word limit.
A long signature may require shortening the draft. One revision pass addresses the first critique, followed by a fresh copy review.
If the first draft passes, the revision step is instructed to preserve it exactly. A failed
final review remains held; there is no unbounded retry loop.

## Optional evidence receipts

`evidence_json` is a JSON array with up to six objects, at most 100,000 serialized characters:

| Field | Meaning |
| --- | --- |
| id | Unique stable receipt ID chosen by the operator |
| provider | exa_snapshot, monitor_signal, or source_capture |
| url | Original source HTTPS URL |
| observed_at | When the operator retrieved the receipt; not the event date |
| text / title | Actual returned content; empty evidence is invalid |
| requested_as_of | Required historical cutoff for an Exa Snapshot receipt |
| captured_at | Actual capture timestamp only if the provider returned one; otherwise omit/null |
| entity_domain | Required when a monitor signal's source URL is on a third-party domain; identifies the target |

Historical source receipts must match the target company's domain. A third-party monitor
signal additionally needs explicit entity_domain and still requires primary-source
verification by deeplineagent. It is not a verified signal merely because it has this label.
The base runtime does not fetch Exa or create signal monitors. The optional `--exa` run described in `exa-connection.md` adds automatic historical/current retrieval using Deepline `generic_http_request`. The default is live deeplineagent
research; operators can supply previously retrieved evidence through a mapped field.

Historical comparisons require exact past/current evidence and substantive verbatim text.
Title-only history, unchanged observations and reversed dates are held. A current receipt
can be imported or the current page can be accessed live; imported provenance remains explicit.
`comparison_mode=before_after` forbids falling back to a dated event. Both historical and
current observations must appear in the opening. See `time-machine.md` for input shapes,
current freshness, chronological checks and date precision rules.

## Three observation modes

- historical_change: comparable imported history and accessible current evidence.
- dated_event: a material primary-source event with YYYY-MM-DD or YYYY-MM precision.
- current_condition: supported present condition, enabled only by require_shift=false;
  copy must not imply a new change.

Insufficient is a research result, never an eligible mode. For month-only events, scoring
uses the first day internally to conservatively compute the oldest possible age. The
email preserves month precision and never asserts that internal day as the event date.
Historical cutoff validation prevents future/invalid dates; historical timing strength
remains an audited judgment, not a computed event date.

## Evidence gates and score

current_claim_verified checks the precise factual observation against the accessed current source.
It does not demand proof of private adoption or budget when those were never claimed. The
implication and its uncertainty are judged separately in inference_bounded.

Required: identity_verified, current_claim_verified, temporal_claim_supported,
offer_relevant, buyer_relevant, inference_bounded, meaningful_observation. When ICP is
supplied, icp_fit_verified is also required. contradiction must explicitly be false.
Historical comparisons additionally require historical_claim_verified, material_shift, comparable_observations and before_after_distinct;
dated events require material_shift and freshness. The capability must exactly match one
actual supplied capability. Missing offer/sign-off inputs remain holds regardless of score.

Strengths: evidence, commercial, offer_fit, timing, specificity, each integer 0–4.
Weights: .30, .25, .20, .15, .10, respectively.

`alpha_score = 100 × product(max(.01, strength/4) ** weight)`

The .01 floor keeps arithmetic defined; each dimension below 2 still independently fails.
Default minimum total score is 65. Strengths are a separate model's auditable judgments,
not independently certified facts, measured coefficients or probabilities.

## Copy gates and result

The reviewer evaluates factual support, visible shift/condition, faithful offer and
subject, no fabricated familiarity or outcomes, buyer relevance and specificity.
`works_without_signal` must be false: removing the observation must remove the specific
reason for the rest of the pitch. This is a model critique, not a measured experiment.

Code verifies required fields, word count, subject length, exact supplied CTA, plain
punctuation, bounded implication, no unresolved placeholders and no research-provider
attribution. The lexical checks are secondary to the semantic review and do not prove
truth. A user CTA that itself makes unsupported claims remains held.

Results carry state, subject/body, hold reasons, score, evidence card, source_record_id, source_id and batch_id. Copy outputs also carry comparison_json with the retained before/after evidence.
`sent` is always false. RESEARCH_REQUIRED returns empty copy; COPY_REVIEW_REQUIRED retains
the held draft for inspection; DRAFT_READY_FOR_REVIEW is eligible for human review only.
Record IDs are provenance for downstream review, not authority to write to a CRM or source list.

## Runtime and portability

The bundled graph uses deeplineagent, Python and rules conditionals, executed by
`scripts/graph_runner.py`. All research goes through Deepline; scoring runs locally. The
model configured in the graph is `openai/gpt-5.4`; verify it is still in the AI Gateway catalog.
Advanced model changes require re-testing, not a claim of identical output.
Deepline's managed `exa_contents` tool has no `snapshotAsOf` input, so optional Exa retrieval uses `generic_http_request` with the user's key. If Deepline later exposes a snapshot input, discover its
actual schema before attaching it; never label an imported receipt as a live provider call.
