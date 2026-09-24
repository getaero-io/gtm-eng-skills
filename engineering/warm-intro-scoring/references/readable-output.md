# Clear output rules

Use short sentences. Use active voice. Use one term for each concept.
Apply these rules to the report, source notes, score explanations, and team handoff.
Use ASD Simplified Technical English as a writing guide. Do not claim certified compliance.

## Report order

1. Show the target contact. Include the company and job title. Link target and connector names and person tags or chips to sourced LinkedIn profile URLs. Retain `target_linkedin_url` and `connector_linkedin_url` through scoring and rendering. Never construct a profile URL from a name. Leave names and person tags unlinked when no verified URL exists. Show “LinkedIn URL unavailable.” Never link factor, company or status tags to a person.
2. Lead with a compact comparison of the top three connectors: rank, name, points, one-line relationship summary and review status. Keep each summary to the strongest sourced signal plus useful overlap dates or shared function/location. Do not infer friendship or familiarity.
3. Show up to three highest-ranked paths. Show fewer when fewer exist. Retain declines and review holds beside each score.
4. Show compact point bars for each path. Keep long reasons and all source evidence in expandable details.
5. Show source details and dates on request.
6. Put weight controls in a separate panel.

Use this path order: requester → connector → target.
Label a relationship as unverified when no source confirms it.
A path is a proposed route. It is not proof of access.

## Score table

Use four clear columns: factor, evidence, weight, and points.
State the calculation: points = evidence value × weight.
Show zero points when evidence is missing. State what is missing.
Keep the original score available for comparison.
Keep the review status unchanged when weights change.

Use “Work at the same time” for dated employer overlap.
Use “School at the same time” for dated school overlap.
Use “Investor company link” for shared funding or portfolio evidence.
Use “Board and employer overlap” for a board role during the target's employment.
Use “Needs confirmation” for a path without confirmed relationships or permission.

## Google spreadsheet

Deliver a private Google spreadsheet with the report. Use the same validated results, score model and selected weights. Include these views. The connection roster and its top-three targets can share a tab:

- **All connections:** One row per source connection, including unscored and unresolved records. Include stable ID, name, sourced LinkedIn URL, company, coverage status and reason for any gap. Label company-network candidates separately.
- **Top paths by target:** Up to three ranked connectors per target. Include rank, both names and LinkedIn URLs, points, one-line relationship summary and review status.
- **Top targets by connector:** Up to three ranked targets per connection. Include the same fields. Connections without scored paths remain in All connections.
- **All scored paths:** Every scored pair, including zero scores. Include component points, source references and review holds.
- **Run details:** Model version, selected weights, score date, source dates, coverage counts and artifact link. State that scores rank evidence, not success probability.

For a large run, keep Google Sheets focused on all connections and top-three results. Link the full scored-pair export as a private downloadable file from Run details. Use a complete connector-by-target matrix only when needed. Keep path-level evidence and holds in linked private exports. State which rows appear in the artifact subset; do not describe that subset as the full scored population. Never truncate silently.

Use the artifact's deterministic ranking and tie order. For the reverse view, rank by points and then stable target ID. Record this tie rule in Run details. Do not add filler rows to reach three paths. Do not hide a decline or hold when a score ranks highly. Regenerate the sheet after weight changes; state the saved weight set and export time.

Keep raw contact text literal. Use RAW writes or equivalent text cells so values beginning with `=`, `+`, `-` or `@` cannot become formulas. Use native rich-text links for names and person chips when supported. Otherwise provide explicit LinkedIn URL columns. Never construct formulas from contact text or guess missing URLs.

Do not enable public or link-wide sharing. Read the saved spreadsheet through the native Sheets API. Check tab names, row counts, representative URLs, scores, ranks, ties, unscored records and holds against the validated export. Link the spreadsheet in the final response. If Sheets access fails, deliver local exports and state the blocker; do not claim a Google spreadsheet exists.

## Source notes

State the fact first. Then give the source and date.
Distinguish the date of an event from the date of a data check.
Use a source link when available. Keep database record IDs in source details.
Do not place raw JSON, SQL, or long source IDs in the main report.
Do not replace an unknown value with a negative claim.
Do not call an old profile current because a new source was checked today.

## Scope and style

Prefer sentences of 20 words or fewer in instructions.
Use descriptive sentences of 25 words or fewer when practical.
Keep names, exact titles, source quotes, and technical identifiers intact.
These limits aid review. They do not validate the full ASD vocabulary or standard.

Source: https://www.asd-ste100.org/about_STE.html
