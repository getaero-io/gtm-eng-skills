# HubSpot Nurture Email Template

**Subject:** {{subject_custom}}

**Preview text:** {{preview_custom}}

---

Hi {{contact.firstname}},

{{opening_context_one_sentence}}

{{#value_section}}
{{value_description}}

{{#optional_proof}}
Example: {{proof_point_brief}}
{{/optional_proof}}
{{/value_section}}

{{#cta_section}}
**{{cta_headline}}**

[{{cta_text}}]({{cta_url}})
{{/cta_section}}

{{#optional_secondary}}
Or {{secondary_action}}: [{{secondary_text}}]({{secondary_url}})
{{/optional_secondary}}

{{closing_line}}

— {{owner.firstname}}

---

**Template notes:**
- Use this for nurture sequences that reference a real tool, workflow, or artifact
- Do NOT use for generic "thought leadership" or vague positioning
- Proof points must be verifiable (no invented metrics or logos)
- Keep CTA singular and clear
