// The export tool owns the canonical review layout and Summary computation.
// This helper is the review skill's reusable, explicit choice of that policy. Keep
// it declarative: custom native requests are for intentional deviations, not
// a duplicate implementation of the tool's evolving defaults.
const presentation = {
  preset: 'review',
  include_notes_column: true,
  auto_fit_columns: true,
  freeze_header: true,
  wrap_header: true,
  add_filter: false,
  summary_tab: true,
  summary_tab_name: 'Summary',
};

process.stdout.write(JSON.stringify(presentation));
