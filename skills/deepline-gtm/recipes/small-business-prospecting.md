# Small Business Prospecting

Use this for local SMB discovery like dentists, plumbers, med spas, agencies, or nearby storefronts.

Each step says what to get. Find the tool or prebuilt play for it with `deepline search`, passing what you have and what you need as `--task`, then read its inputs and price with `deepline tools describe <tool>` or `deepline plays describe <play>`.

1. **Discover businesses with a Maps-style local search.** Search by category and place, such as "dentists in Austin, TX". Run one query with a small limit, read the rows, and tune the query before widening. When the target is a map boundary or a radius around a point, use a search that takes an area or coordinates instead of a place name.
2. **Keep one structured row per business:** name, address, phone, website, rating, and the Maps listing URL or id. Overlapping queries return the same business twice; dedupe on the listing id, or on phone plus address.
3. **Resolve the owner and legal entity when the storefront is not enough.** For US businesses, business-registry records give the registered entity, its addresses, and the owner or principal, and a person lookup then reaches that owner directly. Skip this step when the storefront phone or a shared inbox is all the campaign needs.
4. **Recover a contact email.**
   - Start with the business website and its contact page when the row has a normal homepage.
   - Treat Facebook and Instagram profiles as optional sources, not required steps. Use them when the row's only website is a social profile, the official site is missing or thin, or a sample shows the emails sit in Facebook About blocks, Instagram contact fields, bios, link-in-bio pages, or recent posts. Test a profile tool on a few rows before scaling.
   - Write what you find to audit columns such as `facebook_url`, `instagram_url`, `social_email`, `social_email_source`, `social_identity_evidence`, and `social_contact_confidence` instead of overwriting the canonical email.
   - Accept contact data from a social profile only when the profile matches the business on at least two of: name, address, phone, website or booking link, Maps listing.
5. **Scale it as a play.** Once each step works on a sample, run the list through a play so every row keeps its source columns and the run can be exported.

Deepline has prebuilt plays for parts of steps 3 and 4. `deepline search "smb owner"` and `deepline search "business email"` list them; read each one's inputs with `deepline plays describe` before choosing it over a tool.

```bash
deepline search "local business search" --task "I have a business category and a city and need each business's name, phone, address and website"
deepline search "business registry owner" --task "I have a US storefront's name and address and need its legal entity and owner"
deepline search "facebook page contact details" --task "I have a business's Facebook page URL and need its public email and phone"
```
