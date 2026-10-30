# Google Sheets Workflow Guidance

Google Sheets API methods are not currently available as public Deepline tools. Do not assume that an upstream Sheets API method is an executable
Deepline action. Use `deepline tools grep google_sheets` to check the current
catalog and `deepline tools describe <tool-id>` to confirm a returned action
before execution. Use `deepline tools --help` for command syntax.

When an available spreadsheet action supports the workflow, inspect the target
spreadsheet and tabs before writing. Use explicit A1 ranges for known cells,
request only the fields needed, and preserve exact values when formula or date
parsing would change the user's data. Structural edits and cell-value writes
have different input contracts; describe the exact action instead of guessing
an operation name from the upstream REST method.
