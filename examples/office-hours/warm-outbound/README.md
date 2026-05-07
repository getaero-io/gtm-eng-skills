# Warm Outbound From Visitor Intent

Office-hours example from May 7, 2026.

Turn a website visitor identification webhook into a qualified, human-approved outbound lead.

**Related write-up:** [Vector warm outbound pipeline](https://deepline.com/blog/vector-warm-outbound-pipeline)

## Flow

1. Receive a `contact.visited` webhook from a visitor identification tool.
2. Normalize the visitor payload into a stable person, company, and page-view shape.
3. Deduplicate before spending credits: visitor ID, hashed email, LinkedIn URL, name plus domain, then email.
4. If the source provides a LinkedIn URL, use it directly. Only search Google when the source lacks a profile URL.
5. Run deterministic ICP checks before AI scoring.
6. Run an email waterfall only for qualified visitors.
7. Draft a page-aware opener.
8. Post to Slack for approve, skip, or snooze.
9. Send approved leads to Lemlist.

## Files

- `workflow.json` - Deepline cloud workflow skeleton.

## Notes

- Keep the source LinkedIn URL authoritative when present. Google can return stale profile slugs.
- Put human review after enrichment and before the outbound system.
- Do not expose provider spend in customer-facing copy; report only Deepline spend.
