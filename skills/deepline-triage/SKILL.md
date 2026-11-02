---
name: deepline-triage
description: 'Diagnose failing, stuck, partial, or incorrect Deepline Plays, including when no Play is named. Use deepline-gtm for the primitives, reproduce safely, propose an evidence-backed fix, and apply it after approval. For customer troubleshooting; skip platform incident response.'
---

# Deepline Triage

Help a customer understand a Play failure, test a repair safely, and decide what
to change. Diagnose from evidence before proposing a fix.

## Quick Start

Read `deepline-gtm` before investigating and keep it
active throughout. It owns Deepline setup, discovery, command help, Play
inspection/authoring, execution, spend, and delivery. Use those primitives here;
load each skill once rather than restarting when their routing links meet.

This skill adds the debugging method and customer conversation. Begin with
read-only diagnosis using customer-accessible evidence. A platform or provider
incident may need escalation rather than a Play edit; internal incident response
is outside this workflow.

## 1. Find the failing work

Use the supplied Play, run, error, notification link, and time window. When no
Play is named, inspect all workspace-owned Plays and their recent runs, stating
the chosen window and coverage. Include completed runs with failed rows or
incorrect output. Group recurring symptoms, and distinguish confirmed failures
from inaccessible history, intentional waits, or an absence of recent runs.

## 2. Trace the cause

Read the causal error behind the final failure message. Trace the affected row
back through its logs, retained tool response, input, and pinned source revision;
compare with a working run and recent changes. Keep the failed revision distinct
from the current live revision and working draft.

Separate Play defects, valid provider misses, connection issues, and external
failures. An extraction defect needs evidence that the expected value exists
elsewhere or was lost downstream; other populated fields do not make a null
result a bug. If the cause remains unknown, name the gap and the smallest next
check instead of guessing a repair.

Check whether the affected keys have already recovered. A later successful run
or an empty historical export alone cannot establish what happened to them.

## 3. Reproduce and test safely

State one causal hypothesis and choose the smallest test that could disprove it.
Prefer a local fixture made from retained responses. For a source defect, show
the expected case failing before the change and passing after the smallest fix.
Use deepline-gtm for source validation and authoring guidance.

Reproduction must not resend messages, rewrite records, trigger downstream work,
or spend credits without approval. Use simulation or a dry-run mode only when
its behavior actually suppresses those effects. If safe reproduction is
unavailable, explain the limit and propose a bounded verification plan. Do not
reproduce an external outage just to demonstrate it, or hide failures to make a
test pass.

## 4. Propose the repair

Show the customer what failed, the evidence and confidence, the proposed change,
and what the safe test proved. Explain the remaining verification or recovery:
which records it touches, external effects, expected Deepline spend, and whether
publishing immediately changes scheduled or webhook-triggered behavior.

Get approval before updating a saved Play or performing live verification or
recovery. Existing approval for the same scope remains valid. Separate the
future-run fix from historical recovery; do not manufacture a change when none
is warranted.

## 5. Apply and verify through deepline-gtm

Use deepline-gtm to apply the approved repair and perform its execution and
validation workflow, including when resuming a fix someone already applied.
Verify the repaired revision and the original failing case, then reconcile the
original affected keys. Report what is verified, what recovered, and what is
still unresolved or unverifiable; a passing pilot is not full historical recovery.
If verification fails, revisit the cause instead of stacking speculative fixes
or expanding retries and spend.

Finish with the cause, change, observed test results, actual Deepline spend, and
remaining work, following deepline-gtm's delivery guidance. When another person
or agent must continue, provide a paste-ready handoff containing the Play/run and
log links, expected versus observed behavior, established findings, and remaining
approval boundary. This can accompany a failure notification or open-in-agent
entry point without granting permission to repair automatically.
