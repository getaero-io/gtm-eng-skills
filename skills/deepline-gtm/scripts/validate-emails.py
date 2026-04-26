#!/usr/bin/env python3
"""Validate enriched email data against company domains.

Usage:
  python3 ~/.claude/skills/deepline-gtm/scripts/validate-emails.py enriched.csv \
      --email-col email --domain-col domain

Flags rows where the email domain doesn't match the company domain.
Catches previous-employer or wrong-contact emails.

Read-only — the input CSV is never modified.
"""

import argparse
import csv
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('csv_file', help='Path to the CSV file to validate.')
    parser.add_argument('--email-col', required=True, help='Email column name.')
    parser.add_argument('--domain-col', required=True, help='Domain column name.')
    parser.add_argument('--name-col', default='full_name', help='Name column for display (default: full_name).')
    args = parser.parse_args()

    with open(args.csv_file) as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print('No rows found.')
        return

    headers = set(rows[0].keys())
    for flag, col in [('--email-col', args.email_col), ('--domain-col', args.domain_col)]:
        if col not in headers:
            print(f"Error: column '{col}' not found. Available: {sorted(headers)}", file=sys.stderr)
            sys.exit(1)

    mismatches = []
    for r in rows:
        email = r.get(args.email_col, '')
        domain = r.get(args.domain_col, '')
        if email and domain and email.split('@')[-1] != domain:
            mismatches.append(r)
            print(f"MISMATCH: {r.get(args.name_col, '?')} — {r.get(args.email_col)} vs {r.get(args.domain_col)}")

    total = len(rows)
    n = len(mismatches)
    rate = (n / total * 100) if total else 0
    print(f"\n{n}/{total} rows mismatched ({rate:.0f}%)")
    if rate > 20:
        print("WARNING: >20% mismatch — contact-finding step may need re-running with better disambiguation.")


if __name__ == '__main__':
    main()
