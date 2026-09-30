# Google Sheets Workflow Guidance

Google Sheets is best when the workflow already knows the target spreadsheet or can accept one as input. Prefer the `values.*` endpoints for row-and-cell work, and use `spreadsheets.batchUpdate` when the task changes sheet structure.

## Value Ranges

- Use `google_sheets_spreadsheets_values_get` for one range and `google_sheets_spreadsheets_values_batch_get` for several ranges.
- Use `google_sheets_spreadsheets_values_update` to overwrite a fixed range and `google_sheets_spreadsheets_values_append` to add rows to the end of a table.
- Set `valueInputOption` to `USER_ENTERED` when you want Sheets to parse formulas, dates, and numbers as if a user typed them in. Use `RAW` when exact cell payloads must be preserved.

## Data Filters vs A1 Ranges

- Use A1 ranges (`Sheet1!A1:C50`) when the workflow knows the exact cells.
- Use the `*ByDataFilter` endpoints when the workflow targets named slices, developer metadata, or grid ranges that may move as the sheet changes.

## Spreadsheet Structure

- Use `google_sheets_spreadsheets_get` to inspect sheet tabs and spreadsheet properties before making structural edits.
- Use `google_sheets_spreadsheets_batch_update` for operations like adding tabs, resizing columns, protecting ranges, or attaching developer metadata.
- Use `google_sheets_spreadsheets_sheets_copy_to` to clone a tab into a destination spreadsheet without rebuilding it from scratch.

## Metadata

- Use `google_sheets_spreadsheets_developer_metadata_search` when a workflow needs stable references that survive row moves or sheet reshaping.
- Prefer metadata-driven workflows over brittle hardcoded row numbers when a spreadsheet behaves like an application datastore.
