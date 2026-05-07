#!/usr/bin/env python3
"""
Export LinkedIn Event Organizers CSV to Google Sheets.

Creates a new Google Sheet called "LinkedIn Event Organizers - May 2026" with:
- Tab 1: validated_organizers.csv (validated rows, no apify_profile JSON column)
- Tab 2: phase2_event_organizers.csv (all 105 events)

Features:
- Bold header with dark background (#1a1a1a) and white text
- Frozen header row
- Clickable HYPERLINK() formulas for URL columns
- Column widths per spec
- Conditional formatting: green for name_validated=yes, red for no
"""

import csv
import os
import pickle
import sys
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ── Config ────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
# Secrets dir: defaults to .secrets/ next to this script, or override via SECRETS_DIR env var
SECRETS_DIR = Path(os.environ.get("SECRETS_DIR", BASE_DIR / ".secrets"))
CREDENTIALS_FILE = SECRETS_DIR / "gmail.json"
TOKEN_FILE = SECRETS_DIR / "sheets_token.pickle"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

VALIDATED_CSV = BASE_DIR / "validated_organizers.csv"
PHASE2_CSV = BASE_DIR / "phase2_event_organizers.csv"

SHEET_TITLE = "LinkedIn Event Organizers - May 2026"

# Columns to export from validated_organizers.csv (drop apify_profile)
VALIDATED_COLS = [
    "event_name",
    "event_url",
    "event_date",
    "attendees",
    "organizer_company",
    "organizer_full_name",
    "organizer_individual_linkedin",
    "apify_full_name",
    "apify_headline",
    "apify_company_name",
    "apify_company_linkedin",
    "apify_company_website",
    "name_validated",
]

# Column widths in pixels (approx pts: Google Sheets uses pixels)
VALIDATED_WIDTHS = {
    "event_name": 300,
    "event_url": 200,
    "event_date": 150,
    "attendees": 80,
    "organizer_company": 200,
    "organizer_full_name": 180,
    "organizer_individual_linkedin": 200,
    "apify_full_name": 180,
    "apify_headline": 300,
    "apify_company_name": 200,
    "apify_company_linkedin": 200,
    "apify_company_website": 200,
    "name_validated": 120,
}

# URL columns in validated sheet (0-indexed positions)
VALIDATED_URL_COLS = {
    "event_url": 1,
    "organizer_individual_linkedin": 6,
    "apify_company_linkedin": 10,
    "apify_company_website": 11,
}

# Columns to export from phase2_event_organizers.csv
PHASE2_COLS = [
    "event_name",
    "event_url",
    "event_date",
    "attendees",
    "organizer_company",
    "organizer_full_name",
    "organizer_individual_linkedin",
]

PHASE2_URL_COLS = {
    "event_url": 1,
    "organizer_individual_linkedin": 6,
}

# ── Auth ──────────────────────────────────────────────────────────────────────

def get_credentials():
    creds = None
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing existing sheets token...")
            creds.refresh(Request())
        else:
            print("No valid sheets token found. Starting OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
        print(f"Token saved to {TOKEN_FILE}")

    return creds

# ── CSV helpers ───────────────────────────────────────────────────────────────

def load_csv(path, cols):
    """Load CSV and return list of dicts with only the requested columns."""
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            filtered = {}
            for col in cols:
                filtered[col] = row.get(col, "") or ""
            rows.append(filtered)
    return rows


def make_hyperlink(url, label=None):
    """Return a HYPERLINK formula or plain text if URL is empty."""
    url = (url or "").strip()
    if not url or not url.startswith("http"):
        return url
    if label:
        return f'=HYPERLINK("{url}","{label}")'
    return f'=HYPERLINK("{url}")'


def build_row_values(row_dict, cols, url_col_names):
    """Convert a row dict to a list of values, applying HYPERLINK for URL cols."""
    values = []
    for col in cols:
        val = row_dict.get(col, "")
        if col in url_col_names:
            val = make_hyperlink(val)
        values.append(val)
    return values

# ── Sheets API helpers ────────────────────────────────────────────────────────

def hex_to_rgb(hex_color):
    """Convert #rrggbb to {red, green, blue} with 0-1 floats."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return {"red": r / 255, "green": g / 255, "blue": b / 255}


def header_format_request(sheet_id, num_cols):
    """Bold dark-background white-text header row."""
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 0,
                "endColumnIndex": num_cols,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#1a1a1a"),
                    "textFormat": {
                        "bold": True,
                        "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                    },
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat)",
        }
    }


def freeze_row_request(sheet_id):
    """Freeze the first row."""
    return {
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {"frozenRowCount": 1},
            },
            "fields": "gridProperties.frozenRowCount",
        }
    }


def column_width_request(sheet_id, col_index, width_px):
    """Set a single column width."""
    return {
        "updateDimensionProperties": {
            "range": {
                "sheetId": sheet_id,
                "dimension": "COLUMNS",
                "startIndex": col_index,
                "endIndex": col_index + 1,
            },
            "properties": {"pixelSize": width_px},
            "fields": "pixelSize",
        }
    }


def conditional_format_request(sheet_id, col_index, match_value, bg_hex, num_data_rows):
    """Conditional formatting for a specific string value in a column."""
    return {
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [
                    {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "endRowIndex": num_data_rows + 1,
                        "startColumnIndex": col_index,
                        "endColumnIndex": col_index + 1,
                    }
                ],
                "booleanRule": {
                    "condition": {
                        "type": "TEXT_EQ",
                        "values": [{"userEnteredValue": match_value}],
                    },
                    "format": {"backgroundColor": hex_to_rgb(bg_hex)},
                },
            },
            "index": 0,
        }
    }

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    creds = get_credentials()
    sheets_service = build("sheets", "v4", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)

    # ── Load data ──────────────────────────────────────────────────────────────
    print("Loading CSVs...")
    validated_rows = load_csv(VALIDATED_CSV, VALIDATED_COLS)
    phase2_rows = load_csv(PHASE2_CSV, PHASE2_COLS)
    print(f"  validated_organizers: {len(validated_rows)} rows")
    print(f"  phase2_event_organizers: {len(phase2_rows)} rows")

    # ── Create spreadsheet ────────────────────────────────────────────────────
    print(f"\nCreating spreadsheet: {SHEET_TITLE!r}...")
    spreadsheet_body = {
        "properties": {"title": SHEET_TITLE},
        "sheets": [
            {"properties": {"title": "Validated Organizers", "index": 0}},
            {"properties": {"title": "All Events (105)", "index": 1}},
        ],
    }
    spreadsheet = sheets_service.spreadsheets().create(body=spreadsheet_body).execute()
    spreadsheet_id = spreadsheet["spreadsheetId"]
    sheet_ids = {s["properties"]["title"]: s["properties"]["sheetId"]
                 for s in spreadsheet["sheets"]}

    validated_sheet_id = sheet_ids["Validated Organizers"]
    phase2_sheet_id = sheet_ids["All Events (105)"]

    print(f"  Spreadsheet ID: {spreadsheet_id}")

    # ── Write validated sheet ─────────────────────────────────────────────────
    print("\nWriting validated organizers tab...")
    header = VALIDATED_COLS
    data_values = [header]
    for row in validated_rows:
        data_values.append(build_row_values(row, VALIDATED_COLS, set(VALIDATED_URL_COLS.keys())))

    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="Validated Organizers!A1",
        valueInputOption="USER_ENTERED",
        body={"values": data_values},
    ).execute()

    # ── Write phase2 sheet ────────────────────────────────────────────────────
    print("Writing all events tab...")
    header2 = PHASE2_COLS
    data2_values = [header2]
    for row in phase2_rows:
        data2_values.append(build_row_values(row, PHASE2_COLS, set(PHASE2_URL_COLS.keys())))

    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="All Events (105)!A1",
        valueInputOption="USER_ENTERED",
        body={"values": data2_values},
    ).execute()

    # ── Batch formatting requests ─────────────────────────────────────────────
    print("Applying formatting...")
    requests = []

    # Validated sheet formatting
    requests.append(header_format_request(validated_sheet_id, len(VALIDATED_COLS)))
    requests.append(freeze_row_request(validated_sheet_id))

    for col_name, width in VALIDATED_WIDTHS.items():
        col_idx = VALIDATED_COLS.index(col_name)
        requests.append(column_width_request(validated_sheet_id, col_idx, width))

    # Conditional formatting for name_validated column
    name_val_col_idx = VALIDATED_COLS.index("name_validated")
    requests.append(conditional_format_request(
        validated_sheet_id, name_val_col_idx, "yes", "#c6efce", len(validated_rows)
    ))
    requests.append(conditional_format_request(
        validated_sheet_id, name_val_col_idx, "no", "#ffc7ce", len(validated_rows)
    ))

    # Phase2 sheet formatting
    requests.append(header_format_request(phase2_sheet_id, len(PHASE2_COLS)))
    requests.append(freeze_row_request(phase2_sheet_id))

    # Phase2 column widths (use same widths where col names match)
    for col_name in PHASE2_COLS:
        if col_name in VALIDATED_WIDTHS:
            col_idx = PHASE2_COLS.index(col_name)
            requests.append(column_width_request(phase2_sheet_id, col_idx, VALIDATED_WIDTHS[col_name]))

    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests},
    ).execute()

    # ── Print result ──────────────────────────────────────────────────────────
    sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
    print(f"\nDone.")
    print(f"Google Sheet URL: {sheet_url}")
    return sheet_url


if __name__ == "__main__":
    main()
