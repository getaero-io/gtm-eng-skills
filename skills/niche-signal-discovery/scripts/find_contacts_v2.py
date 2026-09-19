#!/usr/bin/env python3
"""Local shortlist export. Paid legacy contact chain retired; use live Deepline plays."""
import argparse
import csv
import sys
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--top", type=int, help="Optional maximum; default all input rows")
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument("--contacts", action="store_true")
    mode.add_argument("--no-contacts", action="store_true")
    parser.add_argument("--roles", help="Use with the live persona play, not this exporter")
    args=parser.parse_args()
    if args.contacts:
        parser.error("Legacy paid orchestration retired. Use deepline-gtm to describe/run the live persona and email plays; no calls made.")
    if args.top is not None and args.top < 1:
        parser.error("--top must be positive")
    if Path(args.input).resolve()==Path(args.output).resolve():
        parser.error("Output must not overwrite input")
    with open(args.input, encoding="utf-8-sig", newline="") as f:
        reader=csv.DictReader(f)
        fields=reader.fieldnames
        if not fields or "domain" not in fields or len(set(fields))!=len(fields):
            parser.error("Input needs distinct headers including domain")
        rows=list(reader)
    if any(None in r or any(v is None for v in r.values()) for r in rows):
        parser.error("Malformed CSV")
    selected=rows if args.top is None else rows[:args.top]
    with open(args.output,"w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader();writer.writerows(selected)
    print(f"Exported {len(selected)} of {len(rows)} rows in input order; all columns retained. No contact discovery.",file=sys.stderr)

if __name__=="__main__": main()
