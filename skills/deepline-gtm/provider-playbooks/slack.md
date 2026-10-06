# slack_message_with_hitl — Agent Guidance

## Native Slack fields and methods

Use `slack_post_message` and `slack_update_message` for ordinary messaging.
They retain new top-level fields and additive fields inside known Block Kit
objects; known field validation still provides early errors. Use
`slack_api_call` with `{ "method": "chat.update", "params": { ... } }` when
Slack's method or content contract is newer than the local schemas. Its
argument object passes through without a Slack field allowlist, and its
description is available through the same `tools search` / `tools describe`
discovery path. Authentication still comes from the workspace connection.

For `slack_api_call` in Plays, use a stable `id` per intended operation.
No `force` flag is needed: every logical invocation has its own result receipt
and provider operation identity. Restoring identical blocks after a loading
update executes again; deterministic replay reuses that invocation's receipt.
Existing named tools retain their historical payload-based cache behavior.

Native API calls do not create human-action waits. For the compact managed
HITL card, keep using `slack_message_with_hitl`; its current inputs and outputs
remain supported. For a Play that owns a full Block Kit layout and needs
multiple Slack-native buttons or repeated rich-card revisions, use
[`slack_wait_for_action`](actions/wait-for-action.md). It posts or updates one
message revision, waits for one button, returns the original Slack `action_id`
and `value`, and lets the Play replace that same card and wait again. It is
optional; it does not replace or deprecate the managed HITL tool.

In a Play, ordinary Slack post/update tools do not install a listener for their
buttons. `deepline plays check` rejects statically visible callback controls
sent that way in authoring edition 8 and later; editions 2–7 warn and edition 1
keeps its legacy validation path. It also warns when it cannot inspect a
dynamic layout. For repeated decisions, consume the
`slack_wait_for_action` result, use a finite retry limit, and pass the prior
message reference to replace and re-arm that same card.

## Files and full Slack API access

Use `slack_upload_file` for attachments. Its fields follow Slack's `filesUploadV2`: use top-level `content` for a text file, `file` for a value to turn into a file, or `file_uploads` to send a batch. `content` is suitable for CSV, HTML, JSON, Markdown, and text. A JSON `file` value is serialized as JSON. Pass a Dataset Handle directly as `file` in a Play and Deepline materializes the full completed dataset as CSV; outside a Play, use `{ "run_id", "path"?, "dataset_id"? }` as the `file` value. Never build a CSV from a handle's bounded preview.

The Slack connection needs the optional `files:write` and `files:read` bot scopes. `files:read` lets Deepline reconcile a lost upload-finalization response with Slack instead of risking a duplicate attachment. If the integration was connected before those scopes were selected, reconnect it. Attachments are limited to 25 MiB. Dataset Handle CSV exports keep the first 50,000 rows, first 500 columns, and only complete rows that fit the byte limit; successful bounded exports report omissions in `meta.file_transport`.

```json
{
  "channel_id": "C0123456789",
  "file": {
    "run_id": "play/account-research/run/run_123",
    "path": "result.accounts"
  },
  "filename": "qualified-accounts.csv",
  "initial_comment": "Accounts ready for review."
}
```

Use `thread_ts` with `channel_id` to attach a file to a parent thread. Slack ignores `blocks` when `initial_comment` is present, matching Slack's API behavior.

`slack_post_message` stays a direct `chat.postMessage` wrapper. Use `slack_upload_file` when a message needs an attachment; it accepts `blocks`, `initial_comment`, and channel/thread destinations on Slack's external-upload completion call.

## Managed HITL card behavior

Posts a message to Slack with buttons you define, pauses the workflow, and resumes when a human clicks a button. Use it whenever a workflow needs a human decision before proceeding.

## Mental model

1. You define **what the human sees** (text, optional blocks, + buttons) and **what data each button carries** (emit).
2. The system posts the message, pauses the workflow, and waits.
3. A human clicks a button.
4. The workflow resumes. The next step receives `selected_option` (the button id) and `event_payload` (the button's emit data merged with Slack metadata).

That's it. One input, one pause, one output.

## Update and re-arm a managed HITL card

Each call still consumes exactly one click. To let a Play offer another choice
after it handles that click, pass the prior result's `message_ref` to the next
`slack_message_with_hitl` call. Deepline updates that Slack message in place
and installs fresh callback data for the next wait; it does not create a new
card or run an automatic retry loop. Supply a different, stable `signal` for
each interaction cycle so late or duplicate clicks cannot resolve a later
wait.

```json
{
  "channel": "C0123456789",
  "text": "No phone was found. Try another source?",
  "message_ref": {
    "channel": "C0123456789",
    "ts": "1712501111.000100"
  },
  "signal": "phone-waterfall-retry-2",
  "buttons": [
    { "id": "retry", "label": "Retry lookup", "style": "primary" },
    { "id": "stop", "label": "Stop" }
  ]
}
```

Use `message_ref` returned by the previous HITL call and a new stable signal
for every subsequent wait. The Slack connection must be able to update the
original bot-authored message. Without `message_ref`, the tool keeps its normal
behavior and posts a new card.

While a Play resumes, the callback preserves the rich content and replaces
consumed buttons with a processing indicator. The Play can then replace the
whole layout with `slack_api_call` / `chat.update` and re-arm the next decision.
Legacy workflow callbacks retain their historical resolved-card rendering.

## Managed phone-waterfall pattern

Use `slack_wait_for_action` for a Play-owned review round, then update the
same message using its returned `message_ref`. Keep a finite retry limit and
an explicit terminal state for retry, stop, and timeout decisions.

The native wait/resume boundary does not yet consistently attach
`toolResponse.rawV2`. Do not assume the ordinary provider-response envelope
for its action result or copy a provider extraction example into this path.
Inspect an existing internal fixture and its declared contract before revising
a deployed review Play. Canonical extraction examples can be added once this
boundary supplies `rawV2` on live and resumed execution.

## Blocks for `slack_message_with_hitl` (Block Kit)

You can provide custom Slack Block Kit blocks to control the message layout. When `blocks` is provided, it replaces the default section block generated from `text`. The system always appends:

- A **status context block** (hourglass / checkmark)
- An **actions block** with your buttons (injected with routing metadata)

**Do NOT include `actions` blocks** in a `slack_message_with_hitl` call — its
interactive buttons are managed via the `buttons` field. For a Play that needs
native Block Kit buttons, use [`slack_wait_for_action`](actions/wait-for-action.md)
instead; it preserves the whole rich card, returns native action IDs/values,
and re-arms the same message on each call.

When `blocks` is provided, `text` is still required — Slack uses it as the notification preview and accessibility fallback.

### Example with blocks

```json
{
  "channel": "C0123456789",
  "text": "New lead: Sarah Chen, VP Marketing at Stripe",
  "blocks": [
    {
      "type": "header",
      "text": { "type": "plain_text", "text": "New Lead for Review" }
    },
    {
      "type": "section",
      "fields": [
        { "type": "mrkdwn", "text": "*Name:*\nSarah Chen" },
        { "type": "mrkdwn", "text": "*Title:*\nVP Marketing" },
        { "type": "mrkdwn", "text": "*Company:*\nStripe" },
        { "type": "mrkdwn", "text": "*Email:*\nsarah@stripe.com" }
      ]
    },
    { "type": "divider" }
  ],
  "buttons": [
    {
      "id": "approve",
      "label": "Approve",
      "style": "primary",
      "emit": { "decision": "approved" }
    },
    {
      "id": "reject",
      "label": "Reject",
      "style": "danger",
      "emit": { "decision": "rejected" }
    }
  ],
  "allow_edit": true
}
```

### Supported block types

Known Block Kit types have field guidance and additive-field passthrough:
`section`, `header`, `divider`, `context`, `image`, `rich_text`, `actions`
(non-HITL only), `input`, `video`, `table`, `markdown`, `file`,
`context_actions`, `task_card`, and `plan`. Unknown block types also pass
through. Slack decides whether a block is valid on the selected surface.

See the [Block Kit reference](https://docs.slack.dev/reference/block-kit/blocks) for full specifications.

## Button schema

```json
{
  "buttons": [
    {
      "id": "hubspot",
      "label": "Push to HubSpot",
      "style": "primary",
      "emit": { "crm": "hubspot", "action": "create_contact" }
    },
    {
      "id": "skip",
      "label": "Skip",
      "style": "danger"
    }
  ]
}
```

Each button has:

| Field   | Required | Description                                                                                   |
| ------- | -------- | --------------------------------------------------------------------------------------------- |
| `id`    | yes      | Unique identifier. Returned as `selected_option` when clicked. Cannot be `"edit"` (reserved). |
| `label` | yes      | Text shown on the button in Slack.                                                            |
| `style` | no       | `"primary"` (green) or `"danger"` (red). Omit for neutral gray.                               |
| `emit`  | no       | Arbitrary key-value data merged into `event_payload` when this button is clicked.             |

Rules:

- 1–5 buttons required.
- Button ids must be unique.
- `"edit"` is a reserved id — use `allow_edit` instead.
- Unknown fields on buttons are rejected (`additionalProperties: false`).

## What the next step receives

When a human clicks a button, the workflow resumes with this output:

```json
{
  "resumed": true,
  "timed_out": false,
  "selected_option": "hubspot",
  "event_payload": {
    "crm": "hubspot",
    "action": "create_contact",
    "selected_option": "hubspot",
    "slack_user_id": "U0123456789",
    "slack_channel_id": "C0123456789"
  },
  "final_text": "Lead: Sarah Chen, VP Marketing at Stripe",
  "edited": false,
  "signal": "workflow:run_1:block_2:slack:hitl",
  "actor": {
    "slack_user_id": "U0123456789",
    "slack_channel_id": "C0123456789"
  },
  "message_ref": {
    "channel": "C0123456789",
    "ts": "1712501111.000100"
  }
}
```

- `selected_option` — the `id` of the button that was clicked.
- `event_payload` — the button's `emit` data merged with Slack signal metadata (`selected_option`, `final_text`, `edited`, `slack_user_id`, `slack_channel_id`, etc). If the button has no `emit`, event_payload only contains the signal metadata. **Merge precedence:** `emit` keys overwrite signal metadata keys on collision — avoid using `selected_option`, `final_text`, `edited`, `slack_user_id`, or `slack_channel_id` as emit keys.
- `final_text` — the message text at the time of the click (may differ from the original if the human used Edit).
- `edited` — whether the human modified the draft text before clicking.

Branch on `selected_option` in the next workflow step to decide what to do.

## allow_edit

Set `"allow_edit": true` to add an Edit button that opens a Slack modal where the human can modify the `text` field. Editing does NOT resume the workflow — the human must still click one of your defined buttons after editing.

Defaults to `false`. Use it when the `text` field contains a draft the human should be able to revise (e.g., a draft email, a message template).

## post_interaction

Controls the post-click message for legacy workflow waits. Play event waits
immediately show a processing state while the Play resumes; the Play can then
update and re-arm the same card with `message_ref`:

```json
{
  "post_interaction": {
    "disable_buttons": true,
    "replace_message": "Decision recorded."
  }
}
```

- `disable_buttons` — remove all buttons from the message after a click (default: true).
- `replace_message` — replace the entire message text with this string.
- `replace_blocks` — replace the entire message with custom Slack blocks (advanced).

This applies to all buttons. There is no per-button `post_interaction`.

## Timeout and continuation

The new `timeout: null` and `on_timeout_mode` options apply to Play calls through `ctx.tools.execute`. Legacy workflow blocks retain their existing timeout contract and reject these new options before posting a card.

```json
{
  "timeout": "30m",
  "on_timeout_mode": "continue"
}
```

Controls what happens when nobody clicks a button before the deadline:

- `timeout` — Optional deadline. A string duration like `"30m"`, `"2h"`, or `"7d"` keeps its existing meaning, including durations below one minute or above 30 days. `null` opts into a 30-day wait. Omitted keeps the artifact's edition-gated default (24h legacy / 7d current).
- `on_timeout_mode` — Explicit `"park"` keeps the Play paused after the card expires; explicit `"continue"` expires the card and returns `timed_out: true` and `message_ref` so your Play can handle the timeout. Omitted preserves the artifact's existing timeout policy, which parks by default. Both explicit modes take precedence over legacy settings.
- `timeout_emit` — Retained for compatibility and ignored by Play event waits. Timeout results have `event_payload: null`; branch on `timed_out`.

**Legacy fields** (`on_timeout`, `timeout_error`) retain their existing artifact-specific behavior when `on_timeout_mode` is omitted. They do not enable continuation in default parked artifacts. Already-armed waits retain their saved timeout policy on replay.

A timeout never selects an approval button. With `"continue"`, the tool call completes and subsequent code runs, so check `timed_out` before performing approval actions. `timeout: null` alone does not enable continuation.

### Persistent review queues with `timeout: null`

Set `timeout: null` for multi-day or persistent review queues where the card should remain active until a human acts (up to the 30-day platform ceiling):

```json
{
  "channel": "C0123456789",
  "text": "Contract review: $250k ACV deal with Acme Corp",
  "buttons": [
    { "id": "approve", "label": "Approve", "style": "primary" },
    { "id": "reject", "label": "Reject", "style": "danger" }
  ],
  "timeout": null
}
```

The card will not expire until someone clicks a button (or the 30-day platform ceiling is reached).

### Fallback logic with `on_timeout_mode: "continue"`

When you need to take action after a timeout (e.g., log a note, send a reminder, escalate), use `on_timeout_mode: "continue"`:

```json
{
  "channel": "C0123456789",
  "text": "Approve this vendor payment?",
  "buttons": [
    { "id": "approve", "label": "Approve", "style": "primary" },
    { "id": "deny", "label": "Deny", "style": "danger" }
  ],
  "timeout": "2h",
  "on_timeout_mode": "continue"
}
```

When the timeout fires, the tool response includes:

```json
{
  "resumed": false,
  "timed_out": true,
  "message_ref": {
    "channel": "C0123456789",
    "ts": "1712501111.000100"
  },
  "event_payload": null
}
```

Pass this input to `ctx.tools.execute` in a Play. In subsequent Play code, branch on the tool response's `timed_out` field: handle `true` as expiry, and only perform approval actions when `timed_out` is false and `selected_option` matches the approval button. A completed tool call alone is not proof of human approval.

The `message_ref` contains the channel and timestamp of the expired card, so you can reference it in follow-up actions (e.g., reply in thread, update the card, post a reminder).

### Update the original card after a fallback action

Use `slack_update_message` with the same Slack connection to replace the expired card with what happened next. After the HITL call returns `timed_out: true`, perform the fallback action and pass `message_ref.channel` and `message_ref.ts` to the update tool:

```json
{
  "channel": "C0123456789",
  "ts": "1712501111.000100",
  "text": "No response before the deadline. The lead was assigned to the default owner.",
  "blocks": [],
  "attachments": []
}
```

Use the returned message reference in place of the example IDs. Empty arrays remove the old layout and attachments; supply replacement blocks if you want a formatted summary. This tool uses `chat.update` with the connection's existing `chat:write` scope, so no separate Slack credential is needed. It can only edit messages authored by that bot, and cannot edit ephemeral messages. `post_interaction` configures button-click handling; use this update tool for custom timeout follow-up text.

## Common patterns

### Simple confirmation gate (1 button)

```json
{
  "channel": "C0123456789",
  "text": "About to enrich 500 leads. This will cost ~$25.",
  "buttons": [{ "id": "confirm", "label": "Go ahead", "style": "primary" }]
}
```

### Approve / reject with editable draft

```json
{
  "channel": "C0123456789",
  "text": "Hi John, we'd love to set up a call to discuss...",
  "buttons": [
    {
      "id": "approve",
      "label": "Send",
      "style": "primary",
      "emit": { "decision": "send" }
    },
    {
      "id": "reject",
      "label": "Drop",
      "style": "danger",
      "emit": { "decision": "drop" }
    }
  ],
  "allow_edit": true
}
```

### Multi-option CRM routing (5 buttons)

```json
{
  "channel": "C0123456789",
  "text": "New lead: Sarah Chen, VP Marketing at Stripe. Which CRM?",
  "buttons": [
    {
      "id": "hubspot",
      "label": "HubSpot",
      "style": "primary",
      "emit": { "crm": "hubspot" }
    },
    {
      "id": "salesforce",
      "label": "Salesforce",
      "emit": { "crm": "salesforce" }
    },
    { "id": "pipedrive", "label": "Pipedrive", "emit": { "crm": "pipedrive" } },
    { "id": "attio", "label": "Attio", "emit": { "crm": "attio" } },
    { "id": "skip", "label": "Skip Lead", "style": "danger" }
  ]
}
```

Next step branches: `if selected_option === "skip"` → end; otherwise `event_payload.crm` tells you which API to call.

## Using HITL in a workflow

A Deepline workflow is a `commands` array. Each command has an `alias`, a `tool`, and a `payload`.

**Important — `row` access differs by step type:**

| Step type                        | Access pattern                  | Example                             |
| -------------------------------- | ------------------------------- | ----------------------------------- |
| HITL (`slack_message_with_hitl`) | `row.<alias>.selected_option`   | `row.qualify.selected_option`       |
| JavaScript (`run_javascript`)    | `row.<alias>.result.your_field` | `row.draft_email.result.email_body` |

HITL output is stored **flat** — no `.result` wrapper. JS output is wrapped in `{ result, status, meta }`.

**Template interpolation** in tool payloads uses `{{...}}` mustache syntax, NOT `${...}` JS template literals:

```
"text": "{{row.draft_email.result.email_body}}"     ← correct
"text": "${row.draft_email.result.email_body}"       ← WRONG, won't interpolate
```

Here's a 3-step workflow: qualify a lead via HITL, branch on the decision, then post the draft email for approval.

```json
{
  "name": "lead_qualify_and_outbound",
  "publish": true,
  "config": {
    "version": 1,
    "commands": [
      {
        "alias": "qualify",
        "tool": "slack_message_with_hitl",
        "payload": {
          "channel": "C07V9TZ4MSQ",
          "text": "New lead: Sarah Chen, VP Marketing at Stripe.\nEmail: sarah@stripe.com\n\nHow should we classify this lead?",
          "buttons": [
            {
              "id": "hot",
              "label": "Hot Lead",
              "style": "primary",
              "emit": { "qualification": "hot" }
            },
            {
              "id": "warm",
              "label": "Warm Lead",
              "emit": { "qualification": "warm" }
            },
            { "id": "disqualify", "label": "Disqualify", "style": "danger" }
          ],
          "timeout": "2h",
          "on_timeout": "return_null"
        }
      },
      {
        "alias": "draft_email",
        "tool": "run_javascript",
        "payload": {
          "code": "const q = row.qualify; if (q.timed_out || q.selected_option === 'disqualify') return { skip: true }; const isHot = q.selected_option === 'hot'; const body = isHot ? 'Hi Sarah, I\\'d love to set up a quick demo call this week...' : 'Hi Sarah, we published a playbook you might find useful...'; return { skip: false, email_body: body, qualification: q.selected_option };"
        }
      },
      {
        "alias": "approve_email",
        "tool": "slack_message_with_hitl",
        "payload": {
          "channel": "C07V9TZ4MSQ",
          "text": "{{row.draft_email.result.email_body}}",
          "buttons": [
            {
              "id": "send",
              "label": "Approve & Send",
              "style": "primary",
              "emit": { "decision": "send" }
            },
            {
              "id": "drop",
              "label": "Drop",
              "style": "danger",
              "emit": { "decision": "drop" }
            }
          ],
          "allow_edit": true,
          "timeout": "4h",
          "on_timeout": "return_null"
        }
      }
    ]
  }
}
```

### How data flows between steps

```
Step 1 (qualify)                    Step 2 (draft_email)                Step 3 (approve_email)
┌──────────────────┐               ┌──────────────────┐               ┌──────────────────┐
│ HITL: 3 buttons  │               │ JS: reads Step 1 │               │ HITL: approve or │
│                  │──output──────▶│ via row.qualify   │──output──────▶│ drop the email   │
│ Waits for human  │               │ (flat, no .result)│               │ allow_edit: true  │
└──────────────────┘               └──────────────────┘               └──────────────────┘
```

- **Step 1** posts to Slack with 3 buttons, pauses, resumes when human clicks.
- **Step 2** is a `run_javascript` step. It reads Step 1's HITL output at `row.qualify.selected_option` (flat — no `.result`). If the human disqualified the lead or it timed out, it returns `{ skip: true }`. Otherwise it constructs an email draft.
- **Step 3** is another HITL step. The `text` field uses `{{row.draft_email.result.email_body}}` (mustache template, `.result` because it's reading a JS step). `allow_edit: true` lets the human revise it. After approval, `row.approve_email.final_text` contains the final email body.

### Key patterns

**Reading prior HITL output:** `row.<alias>.selected_option` gives you the button ID. `row.<alias>.event_payload` gives you the button's emit data. `row.<alias>.final_text` gives you the (possibly edited) text. No `.result` wrapper.

**Reading prior JS output:** `row.<alias>.result.your_field` — JS steps wrap output in `{ result, status, meta }`.

**Template interpolation in payloads:** Use `{{row.<alias>.field}}` mustache syntax. For JS outputs: `{{row.<alias>.result.field}}`. For HITL outputs: `{{row.<alias>.selected_option}}`.

**Branching:** Use a `run_javascript` step between HITL steps to inspect the prior result and decide what to do next. Return a flag like `{ skip: true }` that downstream steps can check.

**Passing data forward:** You don't need to stuff lead data into every button's `emit`. The workflow engine carries all step outputs in `row`. Any step can read any prior step's output via the patterns above.
