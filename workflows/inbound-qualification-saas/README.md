# Inbound Qualification — SaaS / GTM Tool

A Deepline cloud workflow that qualifies inbound SaaS / GTM-tool signups and routes Enterprise / in-house GTM teams to one HubSpot list (which fires your standing sales sequence) and Agencies / Consultants to a different HubSpot list (which fires a partnerships sequence).

## What it does

Triggered by HubSpot's `contact.creation` webhook (or any inbound form):

1. **Parses the contact event** — handles HubSpot's array webhook payload OR direct test payloads
2. **Validates the email** via LeadMagic
3. **Enriches the company** via Deepline native (skipped on personal email domains)
4. **Enriches the contact** via deepline_native → crustdata waterfall
5. **Scrapes the homepage** for AI classification context
6. **Classifies** via Sonnet 4.6 into one of:
   - `enterprise` — in-house GTM/RevOps/Marketing/Sales team selling its own product
   - `agency` — services business doing outbound on behalf of clients
   - `disqualified` — competitor / spam / job seeker / not actually doing GTM
7. **Routes** with route-specific Slack channel + HubSpot list ID
8. **Posts a Slack brief** with [Enroll in Sales Sequence] [Edit] [Skip] buttons

## Why split enterprise vs agency

Both are valid customers but want different motions:
- **Enterprise** wants a 1:1 sales conversation about their own pipeline — gets booked into a sales rep's calendar
- **Agency** wants to talk partnerships and on-behalf-of pricing — different rep, different sequence

## Why one shared HubSpot Sequence (instead of per-lead drafted emails)

Drafting fresh emails for every signup is expensive ($0.20-0.30 per lead in Sonnet calls), inconsistent across leads, and harder to A/B test. Better pattern: define ONE sequence in HubSpot's UI, edit it as needed, and let HubSpot's native Sequence engine handle delivery, click tracking, reply detection, and unenrollment.

This workflow's job is to qualify + route. The sequence itself lives in HubSpot.

## Deploy

```bash
# 1. Set up HubSpot side first (~5 min in HubSpot UI):
#    a. HubSpot → Lists → Create two manual lists:
#       - "Inbound — enterprise"
#       - "Inbound — partnerships"
#       Note the list IDs from the URL bar.
#    b. HubSpot → Automation → Sequences → Create sequence with your 3-touch outbound copy
#       (sample copy below). Set From-name to your sales rep.
#    c. HubSpot → Automation → Workflows → New contact-based workflow:
#       - Trigger: contact list memberships → has been added to → "Inbound — enterprise"
#       - Action: enroll in your sequence
#    d. (Optional) Same for partnerships — create a separate sequence + workflow on that list.

# 2. Edit workflow.json:
#    - Replace SLACK_CHANNELS map values
#    - Replace HUBSPOT_LISTS map with the IDs from step 1a
#    - Replace REPLACE_ME_REP_NAME with your sales rep's first name
#    - Replace REPLACE_ME_PRODUCT_NAME with your product name
#    - Replace REPLACE_ME_CAL_LINK if you re-enable per-lead drafted emails

# 3. Apply:
deepline workflows apply --payload "$(cat workflow.json)" --json

# 4. Wire HubSpot webhook → this workflow's webhook URL:
#    HubSpot → Settings → Integrations → Webhooks → Create subscription
#    Type: contact.creation
#    Target URL: <webhook URL printed by step 3>
```

## Sample sequence copy (for HubSpot UI)

**Day 0 — Welcome**
- Subject: `Welcome to {{ product }}`
- Body:
  ```
  Hi {{ contact.firstname }},

  It's <REP> from <PRODUCT>. Glad you signed up. Let me know if you have any questions as you get going.

  If you want to hop on a quick call to talk through how to get the most value out of the platform, here's my calendar: <CAL_LINK>

  What's the one outbound or enrichment problem you're hoping to solve first?

  <REP>
  ```

**Day 3 — Specific use case**
- Subject: `One way teams are using <PRODUCT>`
- Body:
  ```
  Hi {{ contact.firstname }},

  The pattern I see most often with new <PRODUCT> users is this: they pick one specific outbound or enrichment workflow that's bottlenecking their team and rebuild it as a repeatable pipeline. Once that's working, the next two follow naturally.

  If you want to walk through what that first pipeline could look like for your team, my calendar is <CAL_LINK>

  What would you most want to automate first?

  <REP>
  ```

**Day 7 — Light nudge**
- Subject: `Still here if useful`
- Body:
  ```
  Hi {{ contact.firstname }},

  Not sure if <PRODUCT> ended up clicking for you yet. If you're stuck or just want a second pair of eyes on a workflow, I'm happy to take a look together.

  Grab time here whenever it makes sense: <CAL_LINK>

  Is there one specific thing about the platform that's still unclear?

  <REP>
  ```

## Pair with slack-button-listener

The Approve / Edit / Skip buttons in this workflow's brief carry lead context in the button `value` so the listener can recover it without a Slack history read:

```
approve|enterprise|<domain>|<lead_name>|<hubspot_contact_id>|<hubspot_list_id>
```

Wire the [`slack-button-listener`](../slack-button-listener/) workflow as your Slack app's interactivity URL. On Approve, the listener calls `hubspot_add_records_to_list` with the contact_id + list_id from the button value, which fires the HubSpot Workflow → Sequence enrollment chain.
