# Workflows

Reference Deepline cloud workflows for common GTM patterns. Each workflow is a JSON apply-payload you can deploy via `deepline workflows apply`.

## What's in here

| Workflow | Use case |
|---|---|
| [`inbound-qualification-cpg`](inbound-qualification-cpg/) | CPG/DTC brand signups: detect retail-presence via Storepoint/Stockist/Closeby/Storerocket/Storemapper/Bullseye/Brandify locator widgets, classify CPG vs non-CPG, score, route to qualified/manual-review/partner-referral, draft rep brief + outbound email + LinkedIn DM |
| [`inbound-qualification-saas`](inbound-qualification-saas/) | SaaS / GTM-tool signups (e.g. signups from a HubSpot form): enrich, classify enterprise/in-house vs agency/consultant, route to two HubSpot lists that trigger different sequences |
| [`slack-button-listener`](slack-button-listener/) | Listens for Approve & Send / Edit / Skip button clicks on Slack briefs and acknowledges in-thread. Pair with either inbound-qualification workflow above. |

## How to deploy

Each workflow folder has:

- `workflow.json` — the apply payload (with placeholders for IDs, channels, secrets)
- `README.md` — what it does, the wiring instructions, and which placeholders to fill in

Edit the placeholders, then:

```bash
deepline workflows apply --payload "$(cat workflows/<name>/workflow.json)" --json
```

The response includes the generated webhook URL — point your form / HubSpot / Slack interactivity URL at that.

## Common patterns these illustrate

- **Block Kit Slack briefs with interactive buttons** (Approve / Edit / Skip) carrying lead context in the button `value` so the listener doesn't need to read message history
- **Per-route channel routing** via a constant map at the top of each workflow
- **Cost-efficient retail-locator detection**: regex-sniff embed key from one Firecrawl scrape, then call the widget's free public JSON API directly via `generic_http_request` (zero per-call cost)
- **Sonnet 4.6 with structured-output schemas** for classification + draft generation
- **Waterfall contact enrichment** (deepline_native → crustdata) with first-result-wins
- **Webhook → cloud workflow** trigger pattern with payload normalization for both HubSpot's array shape and direct test payloads

## What's intentionally NOT in here

- Real org/workspace IDs, webhook URLs, Slack channel IDs, HubSpot list IDs — placeholders only
- Real test brand domains (use your own)
- Secrets like Meta Pixel ID, LinkedIn Conversion Rule ID — placeholders gated behind `run_if_js: return false` until you wire them in
- Any production CRM/list IDs

These workflows are templates. Read each `README.md` for the placeholders you need to fill before deploying.
