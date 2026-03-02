# GTM Definitions And Defaults

Use this file as the default interpretation layer for GTM workflows when the user has not provided explicit definitions.

## Override Rule

- User-specified definitions always win.
- If a term is not specified by the user, apply the default below.
- For paid full runs, include active defaults in the approval assumptions summary.

## Core Defaults

| Term | Default | Notes |
|---|---|---|
| `job_change` | lookback window = 12 months | Treat a person as "job changed" when the move is within the last 12 months unless overridden. |
| `recent_funding` | lookback window = 12 months | Use for "recently funded" targeting when the user does not specify recency. |
| `hiring_acceleration` | window = 90 days | Compare current hiring signals over the last 90 days. |
| `new_exec_hire` | lookback window = 12 months | Applies to VP/CRO/CMO or equivalent leadership move signals. |
| `verification_success` | `email_status == "valid"` | Treat `catch_all` and `unknown` as unresolved unless the user accepts risk. |
| `pilot_scope` | first 1-2 rows | Default pilot size is `--rows 0:1` unless the user requests a different sample. |

## Output Rule

When a workflow depends on one of these terms, do not leave the interpretation implicit. Use either:

1. user-provided definition, or
2. the default from this file.
