#!/usr/bin/env python3
"""Evidence-first descriptive signal analysis. Stdlib only; never emits scoring weights."""
import argparse
import csv
import hashlib
import json
import math
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

csv.field_size_limit(sys.maxsize)
VERSION = "2.0"
BAD = {"failed", "error", "no_result", "not_found", "permission_blocked", "pending", "running"}
BOILERPLATE = re.compile(r"\b(equal opportunity|genetic information|protected veteran|all rights reserved|cookie policy)\b", re.I)
NEGATION = re.compile(r"\b(no longer|do not|does not|don't|doesn't|didn't|haven't|hasn't|not using|without|never|not|no)\b", re.I)
UNCERTAIN = re.compile(r"\b(may|might|considering|evaluating|formerly|previously|hypothetical)\b", re.I)
STOP = set("a an and are as at be been but by can do for from has have how i if in into is it its of on or our that the their this to was we were what when which who will with you your".split())

def normalize(text):
    return unicodedata.normalize("NFKC", text).replace("\u2019", "'").replace("\u2011", "-")

def pattern(term):
    if not isinstance(term, str) or not term.strip():
        raise ValueError("Terms must be nonempty strings")
    term = normalize(term.strip())
    if "*" in term[:-1] or term == "*":
        raise ValueError("Only an explicit trailing prefix wildcard is supported")
    stem = term.endswith("*")
    if stem and len(term[:-1]) < 3:
        raise ValueError("Prefix wildcards need at least three characters")
    body = re.escape(term.rstrip("*"))
    body = body.replace(r"\ ", r"[ \t\r\n-]+")
    return re.compile(r"(?<!\w)" + body + (r"\w*" if stem else "") + r"(?!\w)", re.I)

def substring_match(text, keyword):
    """Compatibility name; semantics are now boundary-aware, NOT substring."""
    return bool(pattern(keyword).search(normalize(text)))

def sentences(text):
    # Keep original text for exact evidence. Do not build phrases across sentences.
    for part in re.split(r"(?<=[.!?])\s+|\n+", text):
        sentence = part.strip()
        if sentence and not BOILERPLATE.search(sentence):
            yield sentence

def occurrences(text, terms):
    for sentence in sentences(text):
        normalized = normalize(sentence)
        for term in terms:
            for match in pattern(term).finditer(normalized):
                before = normalized[max(0, match.start()-90):match.start()]
                # Scope the heuristic to the nearest contrast/clause.
                before = re.split(r"[,;]|\b(?:but|however)\b", before, flags=re.I)[-1]
                after = normalized[match.end():match.end()+55]
                before = re.sub(r"\bnot only\b", "", before, flags=re.I)
                negative = bool(NEGATION.search(before)) or bool(re.match(
                    r"\s+(?:is|was)\s+(?:not|no longer)\b", after, re.I))
                uncertain = bool(UNCERTAIN.search(before))
                yield {"term": term, "quote": sentence,
                       "polarity": "negative" if negative else "uncertain" if uncertain else "affirmative"}

def _website_failure(data):
    """Provider success does not establish that the requested page was fetched."""
    for record in (data, data.get("metadata"), data.get("meta")):
        if not isinstance(record, dict):
            continue
        if record.get("ok") is False or record.get("success") is False or record.get("error"):
            return "error"
        state = str(record.get("status", "")).strip().lower()
        if state in BAD:
            return state
        codes = [record[key] for key in ("statusCode", "http_status") if record.get(key) is not None]
        if state.isdigit() or type(record.get("status")) in (int, float):
            codes.append(record["status"])
        for code in codes:
            if type(code) in (int, float) and math.isfinite(code) and int(code) == code:
                code = str(int(code))
            if not re.fullmatch(r"\d{3}", str(code).strip()):
                raise ValueError("Website HTTP status must be a three-digit code")
            if not (200 <= int(code) < 300 or int(code) == 304):
                return "error"
    return None

def _unwrap(data, kind):
    """Only known response envelopes; never guess the first arbitrary array."""
    for _ in range(10):
        if isinstance(data, list):
            return data, "success"
        if not isinstance(data, dict):
            raise ValueError("Unsupported source payload type")
        if kind == "website":
            failure = _website_failure(data)
            if failure:
                return [], failure
        if data.get("ok") is False or data.get("error"):
            return [], "error"
        state = str(data.get("status", "")).lower()
        if state in BAD:
            return [], state
        if isinstance(data.get("meta"), dict):
            code = data["meta"].get("status")
            if isinstance(code, int) and code >= 400:
                return [], "error"
        if kind == "website" and any(k in data for k in ("text", "markdown", "content")):
            return [data], "success"
        keys = ("results", "pages") if kind == "website" else ("listings", "jobs", "job_listings")
        for key in keys:
            if key in data:
                if not isinstance(data[key], list):
                    raise ValueError(f"{key} must be an array")
                return data[key], "success"
        if "toolResponse" in data:
            data = data["toolResponse"]
        elif "rawV2" in data:
            data = data["rawV2"]
        elif "raw" in data:
            data = data["raw"]
        elif "data" in data:
            data = data["data"]
        elif "result" in data:
            data = data["result"]
        else:
            raise ValueError("Unsupported source envelope; add an explicit adapter")
    raise ValueError("Source envelope too deeply nested")

def source(cell, kind):
    if cell is None or not str(cell).strip() or str(cell).strip() == "null":
        return [], "missing"
    try:
        data = json.loads(cell) if isinstance(cell, str) else cell
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Malformed {kind} JSON; wrap raw text explicitly") from exc
    items, state = _unwrap(data, kind)
    documents = []
    unavailable = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Source rows must be objects")
        if kind == "website":
            failure = _website_failure(item)
            if failure:
                unavailable.append(failure)
                continue
        info = item.get("job_details", item.get("attributes", item)) if kind == "jobs" else item
        if not isinstance(info, dict):
            raise ValueError("Invalid nested source record")
        title = info.get("title", info.get("job_title", ""))
        body = (info.get("description", info.get("job_description", ""))
                if kind == "jobs" else info.get("text", info.get("markdown", info.get("content", ""))))
        if body is None: body = ""
        if title is None: title = ""
        if not isinstance(body, str) or not isinstance(title, str):
            raise ValueError("Source text/title must be strings")
        url = info.get("url", info.get("job_url", item.get("url", ""))) or ""
        if not isinstance(url, str):
            raise ValueError("Source URL must be a string")
        if kind == "jobs" and not title and not body:
            raise ValueError("Unrecognized job record, not a valid empty job list")
        if kind == "website" and not body.strip():
            unavailable.append("empty")
            continue
        documents.append({"title": title, "description": body, "url": url,
                          "text": f"{title}\n{body}" if kind == "jobs" else body,
                          "source_type": "job_listing" if kind == "jobs" else "website"})
    if kind == "website" and unavailable:
        # Retain successful page evidence, but partial collection cannot prove absence.
        state = "partial" if documents else next((s for s in unavailable if s != "empty"), "empty")
    elif kind == "website" and not documents and state == "success":
        state = "empty"  # Empty scrape is NOT observed absence.
    return documents, state

def parse_website_content(cell):
    docs, _ = source(cell, "website")
    return " ".join(d["text"] for d in docs).lower(), docs

def parse_job_listings(cell):
    docs, _ = source(cell, "jobs")
    return docs, " ".join(d["text"] for d in docs).lower()

def auto_detect_columns(headers):
    normalized = [h.strip().lower() for h in headers]
    result = []
    for name in ("website", "jobs"):
        hits = [i for i, h in enumerate(normalized) if h == name]
        if len(hits) > 1:
            raise ValueError(f"Duplicate {name} columns")
        result.append(hits[0] if hits else None)
    return tuple(result)

def utc(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Dates must contain a timezone")
    return result

def load_accounts(path, website_col=None, jobs_col=None, status_col="status", partition="all"):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)):
            raise ValueError("Duplicate CSV headers")
        rows = list(reader)
    if "domain" not in headers or status_col not in headers:
        raise ValueError("CSV requires domain and outcome/status columns")
    wc, jc = auto_detect_columns(headers)
    wc = wc if website_col is None else website_col
    jc = jc if jobs_col is None else jobs_col
    if wc is None and jc is None:
        raise ValueError("No website/jobs columns; pass explicit column indices")
    if wc is not None and wc == jc:
        raise ValueError("Website/jobs cannot share a column")
    for index in (wc, jc):
        if index is not None and not 0 <= index < len(headers):
            raise ValueError("Column index out of range")
    groups = defaultdict(set)
    accounts = {}
    duplicate_rows = 0
    for line, row in enumerate(rows, 2):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"Malformed CSV row {line}")
        label = row[status_col].strip().lower()
        if label not in {"won", "lost", "unlabeled", "lookalike"}:
            raise ValueError(f"Unknown status at row {line}: {label}")
        raw_domain = row["domain"].strip().lower()
        parsed = urlparse(raw_domain if "://" in raw_domain else "//" + raw_domain)
        domain = (parsed.hostname or "").removeprefix("www.").rstrip(".")
        if not domain or "." not in domain or " " in domain:
            raise ValueError(f"Invalid domain at row {line}")
        account = row.get("account_id", "").strip() or domain
        group = row.get("parent_id", "").strip() or account
        split = row.get("split", "").strip() or "discovery"
        if split not in {"discovery", "validation"}:
            raise ValueError("split must be discovery or validation")
        groups[group].add(split)
        if len(groups[group]) > 1:
            raise ValueError(f"Parent/account overlaps discovery and validation: {group}")
        if account in accounts and (accounts[account]["status"] != label or
                                    accounts[account]["domain"] != domain):
            raise ValueError(f"Conflicting account outcomes/identity: {account}; define cohort upstream")
        if account in accounts and accounts[account]["parent_id"] != group:
            raise ValueError(f"Conflicting parent for account: {account}")
        if split == "validation":
            for field in ("known_at", "scored_at"):
                if not row.get(field):
                    raise ValueError("Validation requires conservative row known_at and scored_at")
            if utc(row["known_at"]) > utc(row["scored_at"]):
                raise ValueError("Source became known after scoring cutoff")
        docs, coverage = {}, {}
        for kind, index in (("website", wc), ("jobs", jc)):
            try:
                docs[kind], coverage[kind] = source(row[headers[index]], kind) if index is not None else ([], "missing")
            except ValueError as exc:
                raise ValueError(f"Row {line}, {kind}: {exc}") from exc
        if account not in accounts:
            accounts[account] = {"account_id": account, "parent_id": group, "domain": domain,
                                 "status": label, "split": split, "documents": docs, "coverage": coverage}
        else:
            duplicate_rows += 1
            old = accounts[account]
            for kind in docs:
                seen = {(d["url"], d["text"]) for d in old["documents"][kind]}
                old["documents"][kind].extend(d for d in docs[kind] if (d["url"], d["text"]) not in seen)
                if old["coverage"][kind] != coverage[kind]:
                    # Mixed success/error cannot establish observed absence.
                    old["coverage"][kind] = "partial"
    selected = [a for a in accounts.values() if partition == "all" or a["split"] == partition]
    return selected, {"input_rows": len(rows), "unique_accounts": len(accounts),
                      "merged_duplicate_rows": duplicate_rows,
                      "unit": "account; group-aware split, not cluster-adjusted inference"}

def concepts(config):
    if not isinstance(config, dict):
        raise ValueError("Config must be category -> list of phrases/concepts")
    output, seen = [], set()
    for category, entries in config.items():
        if not isinstance(entries, list):
            raise ValueError("Each config category must be a list")
        for entry in entries:
            if isinstance(entry, str):
                name, aliases = entry, [entry]
            elif isinstance(entry, dict):
                name, aliases = entry.get("name"), entry.get("aliases")
            else:
                raise ValueError("Invalid concept")
            if not isinstance(name, str) or not name.strip() or not isinstance(aliases, list) or not aliases:
                raise ValueError("Concept requires name and nonempty aliases")
            aliases = sorted(set(aliases)) if all(isinstance(a, str) for a in aliases) else aliases
            for alias in aliases: pattern(alias)
            key = (category, name.casefold())
            if key in seen: raise ValueError("Duplicate concept in category")
            seen.add(key)
            output.append((category, name, aliases))
    return output

def wilson(k, n):
    if not n: return None
    z = 1.959963984540054
    mid = (k/n + z*z/(2*n))/(1+z*z/n)
    half = z*math.sqrt(k/n*(1-k/n)/n + z*z/(4*n*n))/(1+z*z/n)
    return [max(0, mid-half), min(1, mid+half)]

def fisher(a, b, c, d):
    """Two-sided Fisher test; descriptive account-independence assumption."""
    r1, r2, col = a+b, c+d, a+c
    n = r1+r2
    if not r1 or not r2: return None
    def choose(n, k):
        return math.lgamma(n+1)-math.lgamma(k+1)-math.lgamma(n-k+1)
    def logp(k):
        return choose(r1, k)+choose(r2, col-k)-choose(n, col)
    observed = logp(a)
    return min(1.0, sum(math.exp(logp(k)) for k in range(max(0, col-r2), min(r1, col)+1)
                        if logp(k) <= observed + 1e-10))

def adjust(results):
    eligible = [r for r in results if r["p_value"] is not None]
    order = sorted(eligible, key=lambda r: r["p_value"], reverse=True)
    m = len(order)
    harmonic = sum(1/i for i in range(1, m+1))
    previous = 1.0
    for rank, row in zip(range(m, 0, -1), order):
        previous = min(previous, row["p_value"] * m / rank)
        row["q_bh"] = previous
        row["q_by"] = min(1.0, previous*harmonic)

def analyze(input_path, keywords, tools, job_roles, website_col=None, jobs_col=None,
            status_col="status", partition="all", evidence_limit=12):
    accounts, stats = load_accounts(input_path, website_col, jobs_col, status_col, partition)
    rows = []
    for family, config in (("keywords", keywords), ("tools", tools), ("job_roles", job_roles)):
        for category, name, aliases in concepts(config):
            # Separate source strata; never pool partial website/jobs into one denominator.
            for kind in (("jobs",) if family == "job_roles" else ("website", "jobs")):
                eligible = [a for a in accounts if a["status"] in {"won", "lost"} and a["coverage"][kind] == "success"]
                eligible_ids = {a["account_id"] for a in eligible}
                counts, totals = Counter(), Counter(a["status"] for a in eligible)
                evidence, positives, excluded = [], set(), Counter()
                for a in accounts:
                    positive = False
                    local = []
                    for doc in a["documents"][kind]:
                        # Roles are matched to advertised job TITLE only, never someone mentioned in responsibilities.
                        text = doc["title"] if family == "job_roles" else doc["text"]
                        for hit in occurrences(text, aliases):
                            if hit["polarity"] == "affirmative": positive = True
                            else: excluded[hit["polarity"]] += 1
                            local.append({**hit, "account_id": a["account_id"], "company": a["domain"],
                                          "outcome": a["status"], "url": doc["url"],
                                          "page_title": doc["title"], "source_type": doc["source_type"]})
                    if positive and a["account_id"] in eligible_ids:
                        counts[a["status"]] += 1
                        positives.add(a["account_id"])
                    if local:
                        # Preserve counterevidence without flooding the sample with repeats.
                        for polarity in ("affirmative", "negative", "uncertain"):
                            example = next((e for e in local if e["polarity"] == polarity), None)
                            if example: evidence.append(example)
                buckets = defaultdict(list)
                for example in evidence:
                    buckets[(example["outcome"], example["polarity"])].append(example)
                sample = []
                while buckets and len(sample) < evidence_limit:
                    for key in sorted(list(buckets)):
                        sample.append(buckets[key].pop(0))
                        if not buckets[key]: del buckets[key]
                        if len(sample) == evidence_limit: break
                a, c, wn, ln = counts["won"], counts["lost"], totals["won"], totals["lost"]
                ratio = ((a+.5)/(wn+1))/((c+.5)/(ln+1)) if wn and ln else None
                rows.append({"family": family, "category": category, "signal": name, "aliases": aliases,
                             "source": kind, "won_count": a, "won_observed": wn,
                             "lost_count": c, "lost_observed": ln,
                             "won_prevalence_ci95": wilson(a, wn), "lost_prevalence_ci95": wilson(c, ln),
                             "feature_prevalence_ratio_jeffreys": ratio,
                             "p_value": fisher(a, wn-a, c, ln-c),
                             "q_bh": None, "q_by": None, "positive_account_count": len(positives),
                             "excluded_mentions": dict(excluded),
                             "evidence": sample,
                             "evidence_accounts_total": len({e["account_id"] for e in evidence}),
                             "evidence_mentions_total": len(evidence),
                             "evidence_truncated": len(evidence) > evidence_limit,
                             "status": "exploratory", "scoring_eligible": False})
    adjust(rows)
    stats["outcomes"] = dict(Counter(a["status"] for a in accounts))
    stats["coverage"] = {kind: {label: dict(Counter(a["coverage"][kind] for a in accounts if a["status"] == label))
                               for label in ("won", "lost", "lookalike", "unlabeled")}
                         for kind in ("website", "jobs")}
    return {"schema_version": VERSION, "statistics": stats, "signals": rows,
            "method": {"metric": "P(feature|won) / P(feature|lost), Jeffreys-smoothed; NOT win-rate lift",
                       "multiplicity_family": "all configured concept/source tests in this invocation",
                       "uncertainty": "Wilson marginal intervals; Fisher tests assume independent accounts",
                       "validation": "Exploratory output only. No automatic scoring promotion, even on a validation partition.",
                       "semantic_limit": "Lexical mentions with heuristic polarity; not confirmed use, intent or headcount.",
                       "partition": partition}}

def discover(accounts, max_phrases=500, min_accounts=2, max_n=5):
    """Outcome-blind n-gram proposals from discovery partition only."""
    if max_phrases < 1 or min_accounts < 1 or not 2 <= max_n <= 8:
        raise ValueError("Invalid phrase discovery limits")
    frequency, evidence = defaultdict(set), {}
    for account in sorted(accounts, key=lambda a: a["account_id"]):
        if account["split"] != "discovery": continue
        for kind in ("website", "jobs"):
            for doc in account["documents"][kind]:
                for sentence in sentences(doc["text"]):
                    words = re.findall(r"\b[\w]+(?:['-][\w]+)*\b", normalize(sentence).casefold())
                    for size in range(2, max_n+1):
                        for i in range(len(words)-size+1):
                            tokens = words[i:i+size]
                            if tokens[0] in STOP or tokens[-1] in STOP or all(t.isdigit() for t in tokens): continue
                            phrase = " ".join(tokens)
                            frequency[(kind, phrase)].add(account["account_id"])
                            evidence.setdefault((kind, phrase), {"company": account["domain"],
                                "url": doc["url"], "quote": sentence, "source_type": doc["source_type"]})
    ranked = sorted((key for key, ids in frequency.items() if len(ids) >= min_accounts),
                    key=lambda k: (-len(frequency[k]), -len(k[1].split()), k))
    # Round-robin by source and phrase length prevents short frequent boilerplate dominating every slot.
    buckets = defaultdict(list)
    for key in ranked: buckets[(key[0], len(key[1].split()))].append(key)
    selected = []
    while buckets and len(selected) < max_phrases:
        for bucket in sorted(list(buckets)):
            selected.append(buckets[bucket].pop(0))
            if not buckets[bucket]: del buckets[bucket]
            if len(selected) == max_phrases: break
    return {"schema_version": VERSION, "label_blind": True, "partition": "discovery",
            "candidate_count_before_limit": len(ranked), "truncated": len(selected) < len(ranked),
            "candidates": [{"phrase": phrase, "source": kind, "account_count": len(frequency[(kind, phrase)]),
                            "evidence": evidence[(kind, phrase)], "status": "candidate_not_scoring_rule"}
                           for kind, phrase in selected]}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True)
    for name in ("keywords", "tools", "job-roles"): p.add_argument("--"+name)
    p.add_argument("--output")
    p.add_argument("--website-col", type=int)
    p.add_argument("--jobs-col", type=int)
    p.add_argument("--status-col", default="status")
    p.add_argument("--partition", choices=["all", "discovery", "validation"], default="discovery")
    p.add_argument("--evidence-limit", type=int, default=12)
    p.add_argument("--discover-phrases", action="store_true")
    p.add_argument("--max-phrases", type=int, default=500)
    p.add_argument("--min-phrase-accounts", type=int, default=2)
    p.add_argument("--manifest", help="Validation: frozen_at plus config_sha256 mapping")
    args = p.parse_args()
    try:
        if args.evidence_limit < 1: raise ValueError("evidence-limit must be positive")
        if args.output and Path(args.input).resolve() == Path(args.output).resolve():
            raise ValueError("Output must not overwrite input")
        if args.discover_phrases:
            if args.partition != "discovery": raise ValueError("Mine discovery only, never validation/all")
            accounts, _ = load_accounts(args.input, args.website_col, args.jobs_col, args.status_col)
            result = discover(accounts, args.max_phrases, args.min_phrase_accounts)
        else:
            paths = {"keywords": args.keywords, "tools": args.tools, "job_roles": args.job_roles}
            if not all(paths.values()): raise ValueError("All three configs required for analysis")
            if args.partition == "all": raise ValueError("CLI analysis requires a single partition, not all")
            if args.partition == "validation":
                if not args.manifest: raise ValueError("Validation requires frozen config manifest")
                manifest = json.loads(Path(args.manifest).read_text())
                frozen = utc(manifest["frozen_at"])
                if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != manifest["analyzer_sha256"]:
                    raise ValueError("Frozen analyzer changed")
                for name, path in paths.items():
                    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != manifest["config_sha256"][name]:
                        raise ValueError(f"Frozen config changed: {name}")
                with open(args.input, newline="", encoding="utf-8-sig") as f:
                    for row in csv.DictReader(f):
                        if (row.get("split") or "").strip() == "validation" and frozen > utc(row["scored_at"]):
                            raise ValueError("Config frozen after validation scoring date")
            configs = {name: json.loads(Path(path).read_text()) for name, path in paths.items()}
            result = analyze(args.input, **configs, website_col=args.website_col, jobs_col=args.jobs_col,
                             status_col=args.status_col, partition=args.partition, evidence_limit=args.evidence_limit)
            result["config_sha256"] = {name: hashlib.sha256(Path(path).read_bytes()).hexdigest() for name, path in paths.items()}
        text = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)
        if args.output: Path(args.output).write_text(text+"\n", encoding="utf-8")
        else: print(text)
    except (ValueError, KeyError, TypeError) as exc:
        p.error(str(exc))

if __name__ == "__main__":
    main()
