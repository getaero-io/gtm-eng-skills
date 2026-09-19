# Quality gate

Verify provider/play completion and successful export using the live contract. Do not attribute missing data to OS buffers without evidence. Retry only a diagnosed transient failure within a stated limit. Unchanged storage, schema or authorization failures stop that execution path: retain the error and emit the partial report. Waiting is not a repair.

1. Parse CSV with a CSV reader (quoted newlines invalidate wc -l row counts). Compare expected IDs, duplicate IDs, outcomes, source cells, and run error counts.
2. Require explicit website/jobs columns or explicit indices; never infer source type from position.
3. Normalize known provider envelopes. Add a fixture before accepting a new shape. Malformed/unknown payloads fail loudly.
4. Classify each source before extracting features. A successful provider envelope can contain an HTTP error page; exclude its body from features, retain its receipt and keep the account. Empty website content means unknown coverage. Empty jobs means no returned records for the query, not no vacancies or employees. Errors, misses and partial records remain distinct.
5. Report coverage by source and outcome, along with input population and exclusions. No universal 80% pass mark or preferred direction of missingness.
6. Check entity, parent/brand/location, source URL and exact quote. Syndicated pages and duplicate jobs do not count as independent evidence.
7. Check point-in-time eligibility and config manifest for validation. Keep each source's receipt identity, retrieval time, cache time and publication time separate; unknown times stay unknown. A cached run clock cannot timestamp fresh calls, and replay cannot replace original collection times.
8. Before scaling, independently check the generated extractor's emitted claims against retained text, including matches, nonmatches and source failures. A CTA is not response speed; a form is not a callback requirement; search counts are not accepted roles; applicant or vendor language is not account pain. Separate observed facts from source-grounded buying-need hypotheses and their uncertainty; unsupported interpretations remain unknown. Include rare phrases, negatives, wrong-company text and boilerplate.
9. Check quota/pagination truncation before inferring coverage. Phrase/result limits must be reported.

Run offline regression tests before shipment. New semantic edge cases become fixtures. A passing lexical test suite does not establish that the classifier understands arbitrary language or that the signals predict sales outcomes.
