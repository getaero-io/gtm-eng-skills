# Sumble

Use Sumble only when the workspace has connected its own Sumble API key.
Deepline does not provide a managed Sumble key, does not pay Sumble provider
spend, and should not recommend Sumble as a default fallback when no Sumble key
is configured.

Good fits when a Sumble key is present:

- company discovery and account enrichment
- people discovery, person enrichment, and related-people lookups
- job-post search and job-related contacts
- organization signals and priority signals
- saved organization/contact list management inside the user's Sumble account

Prefer the synchronous people endpoints: `sumble_find_people`,
`sumble_enrich_person`, and `sumble_find_related_people`. Sumble v8 makes
`sumble_people` and `sumble_person_detail` asynchronous start/poll endpoints;
Deepline keeps those disabled until a Sumble polling runtime is implemented.

Avoid Sumble when the caller has not explicitly connected or supplied a Sumble
API key. Pick Deepline-managed providers instead.
