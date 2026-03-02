# Dropleads Playbook

Use Dropleads as a two-phase flow: low-cost segment discovery first, paid enrichment second.

## 1) Start with low-cost discovery

- Use `dropleads_get_lead_count` to size the audience before any paid call.
- Use `dropleads_search_people` (or shared `search_people` on provider `dropleads`) to inspect masked contacts and validate ICP filters (`1` credit per search).
- Tighten filters until sample rows clearly match role, industry, and geo expectations.

## 2) Escalate paid calls only for shortlisted targets

- Run `dropleads_email_finder` for contacts that passed the discovery pass.
- Run `dropleads_mobile_finder` only when phone is required for the workflow.
- Keep pilots small first, then scale after quality checks pass.

## 3) Gate outbound with verifier status

- Treat `invalid`, `catch_all`, and `unknown` as non-send by default.
- Treat `valid` as the only status that passes automatic send gates.
- Respect `credits_charged` in responses for post-execution billing accuracy.

## 4) Practical sequencing

1. Count segment (`dropleads_get_lead_count`).
2. Sample segment (`dropleads_search_people`).
3. Enrich a small batch (`dropleads_email_finder` / `dropleads_mobile_finder`).
4. Verify candidate emails (`dropleads_email_verifier`).
5. Expand only after pilot quality is confirmed.
