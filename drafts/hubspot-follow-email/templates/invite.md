# HubSpot Invite Email Template

**Subject:** {{event_name}} in {{city}} — {{date_short}}

**Preview text:** Join us for {{event_hook}}

---

Hi {{contact.firstname}},

We're hosting **{{event_name}}** in **{{city}}** on **{{date_long}}**.

**What:** {{event_description}}

**When:** {{date_long}} at {{time}}

**Where:** {{venue_name}}

**Speakers:**
- {{speaker_1}} ({{speaker_1_title}})
- {{speaker_2}} ({{speaker_2_title}})

[RSVP here]({{luma_url}})

Capacity is {{capacity}} — we'll confirm your spot within 24 hours.

{{#optional_why}}
This is a good fit if you're working on {{icp_challenge}}.
{{/optional_why}}

See you there,  
{{owner.firstname}}  
{{owner.signature}}
