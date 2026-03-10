---
name: build-tam
disable-model-invocation: true
description: |
  Provider-led account and contact sourcing at scale (coverage completion).
  Use this as the task-specific entrypoint, then execute from the
  canonical GTM docs under gtm-meta-skill.
---

# Provider-Led Account And Contact Sourcing

This skill now follows the same documentation pattern as `gtm-meta-skill`.

## Required read order


1. Read `../gtm-meta-skill/SKILL.md` first for global GTM policy, approval gates, and execution defaults.
2. Read and execute the sourcing workflow at `../gtm-meta-skill/provider-led-account-and-contact-sourcing.md`.

## Where to use this

Use this skill for requests like:
- "we sourced 935K leads and need the last 65K by end of week"
- "we exhausted most strategies and need new lead-sourcing channels"
- "use Deepline + Clay together to finish remaining contact coverage"
- "build a TAM/list from ICP filters, then pull contacts at scale"

## Notes


- Treat `../gtm-meta-skill/provider-led-account-and-contact-sourcing.md` as the canonical workflow.
- Keep this file as a thin routing layer only (no duplicated playbook content).
- On completion, follow `gtm-meta-skill` Section 7 for proactive issue feedback and session-sharing consent.
