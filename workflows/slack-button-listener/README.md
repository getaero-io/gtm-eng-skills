# Slack Button Listener

A Deepline cloud workflow that listens for Slack interactivity events (Approve & Send / Edit / Skip button clicks) on inbound brief messages and acknowledges them in-thread.

## What it does

When a user clicks a button on a brief posted by the inbound-qualification workflows:

1. **`validate_event`** parses Slack's `block_actions` payload, extracts action name + lead context from the button's `value` field
2. **`decide_action`** maps the action to a label (Approved & Sent / Edit requested / Skipped)
3. **`build_reply_payload`** assembles a Block Kit ack reply
4. **`post_thread_reply`** posts the acknowledgment to the same channel

## Button value contract

The inbound-qualification workflows post buttons whose `value` field carries lead context so this listener can recover it without reading message history (which would require additional Slack permissions):

```
<action>|<route>|<domain>|<lead_name>[|<hubspot_contact_id>|<hubspot_list_id>]
```

Example: `approve|enterprise|acme.com|Jane Doe|123456789|46`

## Deploy

```bash
# 1. Edit workflow.json:
#    - Replace SLACK_CHANNELS / channel id mappings if needed
#    - Replace REPLACE_ME_CHANNEL_ID with your inbound channel's actual ID
#    - Replace REPLACE_ME_INBOUND_CHANNEL with the channel name (#-prefixed)

# 2. Apply:
deepline workflows apply --payload "$(cat workflow.json)" --json

# 3. Wire Slack:
#    api.slack.com/apps → your app → Interactivity & Shortcuts
#    - Toggle Interactivity ON
#    - Request URL: <webhook URL printed by step 2>
#    - Save
#    Re-install the app to the workspace if Slack prompts you.
```

## Future extensions

This listener is intentionally minimal — it only acknowledges. The natural extensions:

- **approve** → `hubspot_add_records_to_list` (CRM enrollment) → triggers HubSpot Workflow → Sequence
- **approve** → `smartlead_add_to_campaign` for outbound sequences
- **approve** → `attio_assert_record` to mark deal as Open/Qualified
- **edit** → spawn a re-draft sub-workflow that takes a thread reply as the new instruction
- **skip** → mark Attio deal lost or write `do_not_contact = true` to HubSpot

To wire approve → HubSpot list enrollment, add a step after `decide_action`:

```json
{
  "alias": "enroll_in_hubspot_list",
  "operation": "hubspot_add_records_to_list",
  "payload": {
    "list_id": "{{decide_action.result.data.hubspot_list_id}}",
    "record_ids": ["{{decide_action.result.data.hubspot_contact_id}}"]
  },
  "run_if_js": "return row.decide_action?.result?.data?.action === 'approve' && Boolean(row.decide_action?.result?.data?.hubspot_contact_id);",
  "tool": "hubspot_add_records_to_list"
}
```

You'll need to update the parser to also pull `hubspot_contact_id` and `hubspot_list_id` from the pipe-delimited button value (parts[4] and parts[5]).
