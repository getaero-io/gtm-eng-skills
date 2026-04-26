---
name: build-tam
description: "Build a Total Addressable Market list by sourcing accounts and contacts from providers like Apollo, Crustdata, and PDL."
---

# Provider-Led Account And Contact Sourcing

This skill now follows the same documentation pattern as `deepline-gtm`.

## Required read order

1. Read the phase docs for global GTM policy, approval gates, and execution defaults.
2. Read and execute the sourcing workflow at `finding-companies-and-contacts.md`.

## Where to use this

Use this skill for requests like:
- "we sourced 935K leads and need the last 65K by end of week"
- "we exhausted most strategies and need new lead-sourcing channels"
- "use Deepline + Clay together to finish remaining contact coverage"
- "build a TAM/list from ICP filters, then pull contacts at scale"

## Notes

- Treat `finding-companies-and-contacts.md` as the canonical workflow.
- Keep this file as a thin routing layer only (no duplicated playbook content).
- On completion, follow `deepline-gtm` Section 7 for proactive issue feedback and session-sharing consent.
