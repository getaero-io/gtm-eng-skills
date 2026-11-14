# Connect the user's own contact or company list

Choose the exact source per run. A generic portable package must not contain the author's
file paths, column names or real contacts. A source_kind label alone is not a connection.
A source record ID alone does not perform lookup or writeback.

## Shared brief versus record fields

| Shared setup, editable at the beginning | Each record |
| --- | --- |
| Offer, ICP, CTA, greeting, signature, sender name, settings | Employer domain, company name, first name, role, stable contact/row ID, optional evidence receipts |

A row-specific override can be mapped intentionally. By default, one brief applies to the
selected file. Do not infer an employer from a personal email domain. If the company domain
is missing, resolve it first (see the `resolve-company-domain` skill) before running. Do not
enrich every record just to test the mapping.

## CSV source

1. Ask which file if it has not been named. Inspect it with `deepline csv show --csv FILE --summary`
   and `deepline csv show --csv FILE --rows 0:2`. Do not read a large CSV into context.
2. Save the shared brief as a JSON object of the manual input names (no per-person fields).
   Save a field-map JSON object from input names to actual CSV column names. Required mappings:
   company_domain and source_record_id. Optional: company_name, recipient_name, recipient_role,
   evidence_json, past_observation_json, current_observation_json, comparison_page_path.
3. Preview:

   ```bash
   python3 scripts/run.py --state RUN_DIR --brief SHARED_BRIEF \
     --csv FILE --field-map CONFIRMED_MAP --limit 1
   ```

   The preview prints the first row's exact inputs. A missing mapped column or a row without
   company_domain / source_record_id fails instead of silently substituting another person's data.
4. Add `--start` to run that one record. Inspect the input identity, output source_record_id,
   exact greeting, CTA, signature, terminal verdict and subject/body in the run record.
5. Drop `--limit` (or raise it) for the authorized scope. Results go to
   `RUN_DIR/runs/<batch>/results.jsonl`, one line per record, with a run record per row.

No automatic writeback is included. To push drafts to a CRM or sequencer, that is a separate,
explicitly requested step with the CRM's Deepline tools (`deepline tools search "<crm> update contact"`).

### Per-person comparison mapping

Map the employer domain, first name, role and stable contact/row ID from each person.
Map optional `past_observation_json` and `current_observation_json` from that person's
company evidence columns, or map `evidence_json`. Do not combine duplicate receipt IDs.
JSON strings in scalar columns are supported. The runner never assigns another company's
observations or a shared contact name to every person. Company evidence can be shared
across coworkers only through a verified employer relationship in the source.
Use `source_id` (in the brief) for the list and `batch_id` for the shared version/run label.
These, plus `source_record_id`, survive into ready and held outputs.
See `time-machine.md` for the comparison contract.

### Run at volume

1. Select the intended file or a filtered slice, then preview the scope.
2. Configure the shared brief and map the person/company columns once.
3. Test one or two records and review identity, greeting, before/after claims, exact CTA,
   signature and holds. A file mapping is not proven by a manual company test.
4. Run the authorized scope. Ready/held/failed are separate outcomes; completion is not
   sending. A row that raises an error is written as PIPELINE_ERROR and the batch continues.

This version runs research per person, sequentially. It does **not** automatically deduplicate
company research, prevent replay, write results back, schedule recurrence, or prove batch
throughput. Do not claim those optimizations. Reuse source evidence columns to avoid mismatching
company observations, but do not call that an automatic shared research cache. Actual runtime
and charges vary with branching and research depth. Confirm scope before large runs.
