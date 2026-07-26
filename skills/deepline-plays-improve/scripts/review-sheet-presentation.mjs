const darkBlue = { red: 0.13, green: 0.27, blue: 0.58 };
const white = { red: 1, green: 1, blue: 1 };
const lightBlue = { red: 0.85, green: 0.89, blue: 0.96 };
const lightYellow = { red: 1, green: 0.95, blue: 0.8 };
const darkText = { red: 0.2, green: 0.2, blue: 0.2 };

const presentation = {
  preset: 'none',
  include_notes_column: true,
  auto_fit_columns: true,
  summary_tab: true,
  requests: [
    {
      updateSheetProperties: {
        properties: {
          sheetId: '$results_sheet_id',
          gridProperties: { frozenRowCount: 1 },
        },
        fields: 'gridProperties.frozenRowCount',
      },
    },
    {
      repeatCell: {
        range: {
          sheetId: '$results_sheet_id',
          startRowIndex: 0,
          endRowIndex: 1,
          startColumnIndex: 0,
          endColumnIndex: '$result_column_count',
        },
        cell: {
          userEnteredFormat: {
            backgroundColor: darkBlue,
            textFormat: { foregroundColor: white, bold: true },
            wrapStrategy: 'WRAP',
          },
        },
        fields: 'userEnteredFormat',
      },
    },
    {
      repeatCell: {
        range: {
          sheetId: '$results_sheet_id',
          startRowIndex: 0,
          endRowIndex: '$result_row_count',
          startColumnIndex: '$notes_column_index',
          endColumnIndex: '$result_column_count',
        },
        cell: {
          userEnteredFormat: {
            backgroundColor: lightYellow,
            wrapStrategy: 'WRAP',
          },
        },
        fields:
          'userEnteredFormat.backgroundColor,userEnteredFormat.wrapStrategy',
      },
    },
    {
      repeatCell: {
        range: {
          sheetId: '$results_sheet_id',
          startRowIndex: 0,
          endRowIndex: 1,
          startColumnIndex: '$notes_column_index',
          endColumnIndex: '$result_column_count',
        },
        cell: {
          userEnteredFormat: {
            textFormat: { foregroundColor: darkText, bold: true },
          },
        },
        fields: 'userEnteredFormat.textFormat',
      },
    },
    {
      repeatCell: {
        range: {
          sheetId: '$summary_sheet_id',
          startRowIndex: 0,
          endRowIndex: 1,
          startColumnIndex: 0,
          endColumnIndex: '$summary_column_count',
        },
        cell: {
          userEnteredFormat: {
            backgroundColor: darkBlue,
            textFormat: { foregroundColor: white, bold: true },
          },
        },
        fields: 'userEnteredFormat',
      },
    },
    {
      repeatCell: {
        range: {
          sheetId: '$summary_sheet_id',
          startRowIndex: 9,
          endRowIndex: 10,
          startColumnIndex: 0,
          endColumnIndex: '$summary_column_count',
        },
        cell: {
          userEnteredFormat: {
            backgroundColor: lightBlue,
            textFormat: { bold: true },
          },
        },
        fields: 'userEnteredFormat',
      },
    },
    {
      repeatCell: {
        range: {
          sheetId: '$summary_sheet_id',
          // Include the text header so this range stays non-empty when a
          // dataset has no source columns. The number format is inert on text.
          startRowIndex: 9,
          endRowIndex: '$summary_row_count',
          startColumnIndex: 3,
          endColumnIndex: 4,
        },
        cell: {
          userEnteredFormat: {
            numberFormat: { type: 'PERCENT', pattern: '0.0%' },
          },
        },
        fields: 'userEnteredFormat.numberFormat',
      },
    },
    {
      autoResizeDimensions: {
        dimensions: {
          sheetId: '$summary_sheet_id',
          dimension: 'COLUMNS',
          startIndex: 0,
          endIndex: '$summary_column_count',
        },
      },
    },
  ],
};

process.stdout.write(JSON.stringify(presentation));
