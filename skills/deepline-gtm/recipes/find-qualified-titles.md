---
name: find-qualified-titles
description: "Use when finding real role-holders at known company domains from an ICP, especially prompts like 'find all job titles at these companies', 'find qualified titles', 'find RevOps or marketing-ops buyers', or when exact title discovery should precede paid people search."
---

# Find Qualified Titles

Given a list of companies and an ICP in plain English, find the people who hold the matching roles, starting from each company's real title roster instead of guessed keywords. The roster is free, the ICP match is one small AI call per company, and you spend on contacts only at the end.

This recipe names Deepline's own tools because the method depends on two of them: `company_titles` returns a company's verbatim titles, and `search_contact` is the people search that accepts those titles as lists. Read both contracts with `deepline tools describe` before you build.

## When to use

- The user asks for nuanced functions or real job titles at named companies, such as "AI leadership at Mount Sinai".
- "Find all job titles at these companies", or "what roles exist at X".
- "Find the marketing ops, RevOps, or Salesforce buyers at these accounts."
- Any time you would otherwise guess title keywords and miss real titles, such as "Revenue Architect" for "VP Sales" or "GTM Systems" for "Sales Ops".

Do not start with a paid people search here. The roster answers "what titles exist at this company" for free; people search is for when you already know the persona and need volume.

## Inputs

- A CSV or a list of company domains. A `domain` column is required; `company_name` and `company_linkedin` are optional.
- The ICP in plain English.

## Steps

Author this as one play over the company list, one column per step. For a single company, run the same tools with `deepline tools execute`.

1. **Get each company's title roster.** `company_titles` with the company domain. It is free.
2. **Flatten the roster to a plain list of strings.** The tool declares no getters, so read one persisted row to see where the titles landed (recent runs put them under `output.titles`) before writing the extraction.
3. **Filter the roster to the ICP.** One `deeplineagent` call per company with a `jsonSchema` of `{matched_titles: string[], reasoning: string}`. Spell out what to include and exclude, for example "Marketing Ops, Sales Ops, RevOps, Salesforce admin or architect; senior IC and above; exclude recruiters, finance, support, and plain reps", and tell it to return only exact strings from the list. Pass the full roster; do not trim it first.
4. **Find the holders of the matched titles.** `search_contact` with the domain and `title_lists: [{"name": "icp", "titles": [...]}]`. `titles` must be a real array when the call runs; a CSV cell that only looks like JSON is rejected before the provider is called. Raise `page_size` (default 10, maximum 250) or paginate when many titles matched, or the results are cut off without warning.
5. **Re-check every returned title.** Title-list matching is not exact: results include titles that only contain a listed one, such as "Staff Engineer Heat Transfer Group" for "Staff Engineer" (128 of 380 rows in one run). Each returned row is billed, so drop rows whose `title` is not in the matched list before paying for anything else.
6. **Flatten to one row per contact.** One company yields many people, so this is a file step, not another column. The script is in this skill's `scripts/` directory:

   ```bash
   python3 scripts/flatten-search-contact-persons.py contacts.csv --contacts-col contacts > contact_rows.csv
   ```

7. **Reveal contact data only on the rows the user keeps.** Step 4 returns names, titles, and LinkedIn URLs, never an email or a phone. Ask which channels the user needs, then run the prebuilt email or phone batch play from the skill's working rules on the kept rows. Never enrich the whole set by default.

## Rules that are easy to get wrong

- **Title lists, not title filters.** The matched titles are exact strings from the company's own roster, so `title_lists` resolves every one. `title_filters` is boolean keyword matching, where "operations" also catches "People Operations Intern"; use it only when you did not qualify against the roster and want a broad sweep.
- **`title_lists` exists on `search_contact` only.** `prospector` rejects it with a 422. `prospector` returns the contact and an email in one call from boolean title filters, so consider it only when broad matching is acceptable and the user wants emails on most contacts up front.
- **Supplemental coverage comes after the roster pass.** Other people-search and public-profile tools, found with `deepline search`, can add people the contact search misses. Check the current employer and title before counting one as a match: keyword filters miss real roster titles such as "Director, Mount Sinai AI Assurance Lab".
- **The AI filter is only as good as the ICP prompt.** Be specific about what is in and out.
- For sizing a market instead of qualifying titles at named companies, follow `build-tam.md`.
