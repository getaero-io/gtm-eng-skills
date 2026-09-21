# HubSpot Reminder Email Template

**Subject:** Reminder: {{event_name}} tomorrow

**Preview text:** See you at {{venue_name}} — {{time}}

---

Hi {{contact.firstname}},

Quick reminder: **{{event_name}}** is tomorrow.

**When:** {{date_long}} at {{time}}

**Where:** {{venue_name}}, {{venue_address}}

{{#optional_logistics}}
**Parking:** {{parking_note}}

**Getting there:** {{directions_note}}
{{/optional_logistics}}

We'll have {{agenda_highlight}}.

Looking forward to seeing you there.

— {{owner.firstname}}

[View event details]({{luma_url}})
