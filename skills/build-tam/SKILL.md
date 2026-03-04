---
name: build-tam
disable-model-invocation: true
description: |
  Build a Total Addressable Market (TAM) list using ICP filters.
  Use this as the task-specific entrypoint, then execute from the
  canonical GTM docs under gtm-meta-skill.
---

# Build TAM

This skill now follows the same documentation pattern as `gtm-meta-skill`.

## Required read order


1. Read `../gtm-meta-skill/SKILL.md` first for global GTM policy, approval gates, and execution defaults.
2. Read and execute the TAM playbook at `../gtm-meta-skill/build-tam.md`.

## Notes

- Treat `../gtm-meta-skill/build-tam.md` as the canonical TAM workflow.
- Keep this file as a thin routing layer only (no duplicated playbook content).
- On completion, follow `gtm-meta-skill` Section 7 for proactive issue feedback and session-sharing consent.
