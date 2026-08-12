# Office-hours examples

## Target-account warm-intro workflow

The warm-intro examples form one review-first workflow. Run them in this order:

1. [`target-account-warm-intro-campaign/`](target-account-warm-intro-campaign/)
   owns account qualification, provider policy, canonical identities, buying
   committees, confirmed-versus-inferred org semantics, interaction evidence,
   campaign path scores, direct-outreach review rows, and the deterministic ledger.
   Its fixture runner is offline and performs no activation.
2. [`warm-intro-scoring/`](warm-intro-scoring/) owns the SQLite network store,
   bounded profile enrichment, criteria discovery, explicit target-person scoring,
   and deterministic `lookup.py --csv` output with the target title and score
   components.
3. [`warm-intro-ask-threads/`](warm-intro-ask-threads/) consumes that scorer CSV
   directly and owns grounded model drafts, `approved=false` defaults, manual
   approval, message versions, dry runs, rate limits, atomic send reservations, and
   the SQLite activation log.

The ownership boundaries are intentional. A campaign score never approves a
message, a model draft never approves itself, and only the activation stage may
perform an external send after explicit review.
