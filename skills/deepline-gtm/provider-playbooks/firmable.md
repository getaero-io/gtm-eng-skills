# Firmable

Firmable supports either Deepline-managed access or a workspace-owned API key.
If a workspace connects its own key, that key is preferred for Firmable calls.

- Use `firmable_company_lookup` when you have a company identifier, domain, website, or LinkedIn profile.
- Use `firmable_person_lookup` when you have a Firmable person ID, LinkedIn profile, or email address.
- Use `firmable_people_search` to find people at a known Firmable company ID, then narrow by country, position, seniority, or department.
- Deepline billing is not currently configured for Firmable calls; provider
  charges follow the selected Firmable account.
