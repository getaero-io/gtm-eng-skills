# Firmable

Firmable supports either Deepline-managed access or a workspace-owned API key.
If a workspace connects its own key, that key is preferred for Firmable calls.

- Use `firmable_company_lookup` when you have a company identifier, domain, website, or LinkedIn profile.
- Use `firmable_person_lookup` when you have a Firmable person ID, LinkedIn profile, or email address.
- Use `firmable_people_search` to find people at a known Firmable company ID, then narrow by country, position, seniority, or department.
- Managed company and person lookups cost 3.57 Deepline credits per matched profile, including repeat lookups and profiles without contact details. Phone and email values are included.
- Managed people searches cost 3.57 Deepline credits per non-empty page, including masked rows and repeated searches. Empty searches and documented lookup misses are uncharged.
- These are Deepline data-access service charges. They do not infer Firmable credit consumption from a match; Firmable may make repeat unlocks free in its own account.
- Workspace-owned keys are not charged Deepline provider credits; Firmable manages the provider account's credits.
