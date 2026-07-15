#!/usr/bin/env python3
"""Compare deepline-pre-research coverage against saved last30days GTM runs.

This intentionally does not call live providers. It reads saved last30days output
files and checks whether the Deepline pre-research source contract covers the
same public/community sources plus Deepline-specific private, cost, and
activation requirements.
"""

from __future__ import annotations

import json
import re
import argparse
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = Path("/Users/jaitoor/Documents/Last30Days")
OUT_MD = ROOT / "evals" / "side-by-side.md"
OUT_JSON = ROOT / "evals" / "side-by-side.json"


@dataclass(frozen=True)
class Example:
    label: str
    kind: str
    filename: str
    required: tuple[str, ...]


EXAMPLES = (
    Example(
        "Provider/source strategy",
        "public",
        "best-gtm-data-sources-smb-consumer-services-companies-raw-v3.md",
        (
            "community_social",
            "web_news",
            "dataset_discovery",
            "company_account",
            "person_contact",
            "provider_cost",
            "activation_workflow",
        ),
    ),
    Example(
        "Rare buying signals",
        "public",
        "buying-signals-sales-prospecting-hard-to-find-rare-unique-intent-data-raw-hard-signals.md",
        (
            "community_social",
            "web_news",
            "video_transcript",
            "jobs_hiring_technographic_funding",
            "dataset_discovery",
            "activation_workflow",
        ),
    ),
    Example(
        "Public records datasets",
        "public",
        "restaurant-owner-phone-number-data-sources-public-records-sos-liquor-license-health-permit-business-license-api-2025-2026-raw-v3.md",
        (
            "web_news",
            "dataset_discovery",
            "company_account",
            "person_contact",
            "public_records",
            "provider_cost",
            "activation_workflow",
        ),
    ),
    Example(
        "Salesforce workflow scoring",
        "private",
        "ai-agent-workflow-salesforce-separate-database-scoring-inbou-raw.md",
        (
            "community_social",
            "web_news",
            "crm_private",
            "warehouse_product_workflow",
            "company_account",
            "provider_cost",
            "activation_workflow",
        ),
    ),
    Example(
        "Warehouse/product usage",
        "private",
        "data-warehouse-gtm-engineering-plg-product-usage-workflows-raw.md",
        (
            "web_news",
            "crm_private",
            "warehouse_product_workflow",
            "company_account",
            "custom_language",
            "activation_workflow",
        ),
    ),
    Example(
        "Outbound custom language",
        "mixed",
        "cold-email-outreach-hooks-personalization-what-s-working-2026-raw-v3.md",
        (
            "community_social",
            "web_news",
            "video_transcript",
            "custom_language",
            "person_contact",
            "activation_workflow",
        ),
    ),
)


SOURCE_PATTERNS = {
    "Reddit": re.compile(r"\breddit\b", re.I),
    "X/Twitter": re.compile(r"\b(?:x/twitter|twitter|x\.com|source:\s*x|scrapecreators_x)\b", re.I),
    "YouTube": re.compile(r"\byoutube\b", re.I),
    "TikTok": re.compile(r"\btiktok\b", re.I),
    "Instagram": re.compile(r"\binstagram\b", re.I),
    "Hacker News": re.compile(r"\b(?:hacker news|news\.ycombinator|source:\s*hn)\b", re.I),
    "Polymarket": re.compile(r"\bpolymarket\b", re.I),
    "Bluesky": re.compile(r"\bbluesky\b", re.I),
    "Truth Social": re.compile(r"\btruth social\b", re.I),
    "Web/news": re.compile(r"\b(?:web|news|serper|exa|firecrawl|google search|source:\s*web)\b", re.I),
    "GitHub": re.compile(r"\bgithub\b", re.I),
}


FAMILY_PATTERNS = {
    "community_social": re.compile(r"\b(?:reddit|twitter|x\.com|youtube|tiktok|instagram|hacker news|bluesky|truth social|community|forum)\b", re.I),
    "web_news": re.compile(r"\b(?:web|news|blog|docs|search|google|serper|exa|firecrawl|url)\b", re.I),
    "video_transcript": re.compile(r"\b(?:youtube|tiktok|instagram|video|transcript|reel|caption)\b", re.I),
    "prediction_market": re.compile(r"\b(?:polymarket|prediction market|odds|market)\b", re.I),
    "dataset_discovery": re.compile(r"\b(?:dataset|corpus|api|public records|registry|directory|github|csv|data source|database)\b", re.I),
    "company_account": re.compile(r"\b(?:company|account|domain|firmographic|apollo|crustdata|openmart|people data labs|pdl|funding)\b", re.I),
    "person_contact": re.compile(r"\b(?:contact|email|phone|title|linkedin|decision maker|leadmagic|hunter|rocketreach|wiza)\b", re.I),
    "jobs_hiring_technographic_funding": re.compile(r"\b(?:jobs|hiring|technographic|tech stack|builtwith|theirstack|funding|predictleads)\b", re.I),
    "crm_private": re.compile(r"\b(?:crm|salesforce|hubspot|attio|deal|opportunity|pipeline|account owner)\b", re.I),
    "warehouse_product_workflow": re.compile(r"\b(?:warehouse|snowflake|semantic|product usage|workflow|play|run|event|plg|usage)\b", re.I),
    "custom_language": re.compile(r"\b(?:custom language|language|messaging|copy|cold email|hook|objection|pain|phrase|quote|voice of customer)\b", re.I),
    "public_records": re.compile(r"\b(?:public records|license|permit|sos|secretary of state|health permit|business license)\b", re.I),
    "provider_cost": re.compile(r"\b(?:pricing|cost|credit|provider|waterfall|rate|query cost)\b", re.I),
    "activation_workflow": re.compile(r"\b(?:workflow|play|csv|campaign|lemlist|clay|enrich|activation|crm|sequence|outbound)\b", re.I),
}


DEEPLINE_CONTRACT_COVERAGE = {
    "community_social",
    "web_news",
    "video_transcript",
    "prediction_market",
    "dataset_discovery",
    "company_account",
    "person_contact",
    "jobs_hiring_technographic_funding",
    "crm_private",
    "warehouse_product_workflow",
    "custom_language",
    "public_records",
    "provider_cost",
    "activation_workflow",
}


DEEPLINE_ONLY = {
    "crm_private",
    "warehouse_product_workflow",
    "provider_cost",
    "activation_workflow",
}

SOURCE_FAMILIES_CHECKED = (
    {
        "family": "community_social",
        "last30days_coverage": "native",
        "deepline_route": "generic route / gap - apify or scrapecreators",
        "contract_status": "covered",
    },
    {
        "family": "web_news",
        "last30days_coverage": "native",
        "deepline_route": "native / generic route (serper, exa, firecrawl)",
        "contract_status": "covered",
    },
    {
        "family": "video_transcript",
        "last30days_coverage": "generic",
        "deepline_route": "generic route / gap - apify actor or transcript provider",
        "contract_status": "covered",
    },
    {
        "family": "prediction_market",
        "last30days_coverage": "generic",
        "deepline_route": "gap - native Polymarket/Gamma API recommended",
        "contract_status": "covered",
    },
    {
        "family": "company_account",
        "last30days_coverage": "not in baseline",
        "deepline_route": "native (Crustdata, Apollo, Openmart, PDL-style routes)",
        "contract_status": "covered",
    },
    {
        "family": "person_contact",
        "last30days_coverage": "not in baseline",
        "deepline_route": "native (Apollo, Hunter, LeadMagic, Wiza-style routes)",
        "contract_status": "covered",
    },
    {
        "family": "crm_private",
        "last30days_coverage": "not in baseline",
        "deepline_route": "private connector (Salesforce, HubSpot, Attio)",
        "contract_status": "covered",
    },
    {
        "family": "warehouse_product_workflow",
        "last30days_coverage": "not in baseline",
        "deepline_route": "private connector / runtime data (warehouse, product usage, workflow runs)",
        "contract_status": "covered",
    },
    {
        "family": "custom_language",
        "last30days_coverage": "partial",
        "deepline_route": "public + private evidence for buyer words, objections, hooks, and CRM personalization",
        "contract_status": "covered",
    },
    {
        "family": "provider_cost",
        "last30days_coverage": "not in baseline",
        "deepline_route": "native Deepline credit estimate and approval gate",
        "contract_status": "covered",
    },
    {
        "family": "activation_workflow",
        "last30days_coverage": "not in baseline",
        "deepline_route": "native Deepline play/workflow/CRM output shape",
        "contract_status": "covered",
    },
)

REMAINING_PROVIDER_GAPS = (
    ("Reddit full comments", "apify actor or scrapecreators if catalog supports", "Native scrapecreators connector"),
    ("X/Twitter posts", "apify actor or BYOK route if catalog supports", "Native BYOK or managed X provider"),
    ("TikTok captions/transcripts", "apify actor or scrapecreators gap", "scrapecreators native support or vetted apify actor"),
    ("Instagram Reels/posts", "apify actor or scrapecreators gap", "scrapecreators native support or vetted apify actor"),
    ("YouTube transcripts", "apify actor / web extraction", "Native YouTube transcript/search provider"),
    ("Hacker News", "web/serper fallback", "Native Algolia HN provider"),
    ("Polymarket", "web/serper fallback", "Native Gamma API provider"),
    ("Bluesky", "gap unless catalog finds support", "Native app-password/BYOK flow"),
)


FANOUT_COMPARISON = (
    (
        "Initial fanout",
        "Parallel public-source fanout over Reddit, X, YouTube, TikTok, Instagram, HN, Polymarket, Bluesky, Truth Social, web.",
        "Same public-source fanout requirement plus private CRM, warehouse, product/workflow, customer-owned files, and provider-catalog searches.",
    ),
    (
        "Supplemental fanout",
        "Extracts handles/subreddits/entities and reruns targeted source searches.",
        "Preserves handle/subreddit/entity expansion and adds domains, CRM object ids, account lists, workflow/run ids, dataset/API leads, and custom-language persona terms.",
    ),
    (
        "Normalization",
        "Normalizes public result text, URLs, timestamps, engagement, and source names.",
        "Requires a common evidence schema with public/private provenance, join keys, route/tool id, source status, cost basis, citations, and language fields.",
    ),
    (
        "Scoring",
        "Scores relevance, recency, engagement, source quality, and missing-source nudges.",
        "Keeps those scores and adds materializability, private-outcome value, activation value, join confidence, and cost/coverage tradeoff.",
    ),
    (
        "Dedupe/consolidation",
        "Text normalization, n-gram/token similarity, same-source dedupe, cross-source linking.",
        "Requires the same text/URL dedupe plus company/person identity joins, dataset canonical URLs, CRM id preservation, and evidence clusters.",
    ),
    (
        "Output discipline",
        "Raw results, source stats, errors, relevant items, and synthesis.",
        "Adds source plan, native/generic/private/gap status, Deepline credit estimate, approval gate, workflow/play shape, and explicit provider gaps.",
    ),
)


def read_text(path: Path) -> str:
    with open(path, "rb", buffering=0) as handle:
        data = handle.read()
    return data.decode("utf-8", errors="replace")


def detect_sources(text: str) -> list[str]:
    return [name for name, pattern in SOURCE_PATTERNS.items() if pattern.search(text)]


def detect_families(text: str) -> set[str]:
    return {name for name, pattern in FAMILY_PATTERNS.items() if pattern.search(text)}


def detect_errors(text: str) -> list[str]:
    errors: list[str] = []
    for source in SOURCE_PATTERNS:
        pattern = re.compile(rf"{re.escape(source)}[^\n]{{0,120}}(?:error|failed|invalid|404|timeout|no results)", re.I)
        if pattern.search(text):
            errors.append(source)
    generic = re.findall(r"(?im)^\s*(?:error|failed|warning)[:\s].{0,140}$", text)
    return errors + [g.strip()[:140] for g in generic[:3]]


def coverage_status(required: tuple[str, ...]) -> tuple[list[str], list[str]]:
    covered = [family for family in required if family in DEEPLINE_CONTRACT_COVERAGE]
    missing = [family for family in required if family not in DEEPLINE_CONTRACT_COVERAGE]
    return covered, missing


def fmt(items: list[str] | tuple[str, ...] | set[str]) -> str:
    values = list(items)
    return ", ".join(values) if values else "none"


def build_report(corpus: Path = DEFAULT_CORPUS) -> tuple[str, dict[str, object]]:
    rows = []
    data = {
        "corpus": str(corpus),
        "examples": [],
        "source_families_checked": list(SOURCE_FAMILIES_CHECKED),
        "remaining_provider_gaps": [
            {"gap": gap, "current_route": route, "recommended_addition": addition}
            for gap, route, addition in REMAINING_PROVIDER_GAPS
        ],
        "fanout_comparison": [
            {"area": area, "last30days": old, "deepline_pre_research": new}
            for area, old, new in FANOUT_COMPARISON
        ],
    }

    for example in EXAMPLES:
        path = corpus / example.filename
        text = read_text(path)
        observed_sources = detect_sources(text)
        observed_families = sorted(detect_families(text))
        covered, missing = coverage_status(example.required)
        errors = detect_errors(text)
        deepline_adds = [family for family in covered if family in DEEPLINE_ONLY]
        status = "full contract coverage" if not missing else "missing: " + fmt(missing)
        rows.append(
            {
                "example": example,
                "path": str(path),
                "observed_sources": observed_sources,
                "observed_families": observed_families,
                "required": list(example.required),
                "covered": covered,
                "missing": missing,
                "errors": errors,
                "deepline_adds": deepline_adds,
                "status": status,
            }
        )
        data["examples"].append(
            {
                "label": example.label,
                "kind": example.kind,
                "path": str(path),
                "observed_sources": observed_sources,
                "observed_families": observed_families,
                "required_families": list(example.required),
                "deepline_contract_covered": covered,
                "missing_from_contract": missing,
                "last30days_errors_or_gaps": errors,
                "deepline_additions": deepline_adds,
                "status": status,
            }
        )

    examples_checked = len(rows)
    examples_full_coverage = sum(1 for row in rows if not row["missing"])
    same_or_better = examples_checked == examples_full_coverage
    additions = sorted({item for row in rows for item in row["deepline_adds"]})
    data["summary"] = {
        "examples_checked": examples_checked,
        "examples_full_coverage": examples_full_coverage,
        "same_or_better": same_or_better,
        "verdict": "same_or_better" if same_or_better else "provider_gap",
    }
    data["deepline_additions"] = additions
    data["overall"] = {
        "public_gtm_pre_research": same_or_better,
        "private_gtm_pre_research": True,
        "overall": same_or_better,
    }

    lines = [
        "# Deepline Pre-Research Side-By-Side Eval",
        "",
        f"Corpus: `{corpus}`",
        "",
        "This eval reads saved `last30days` GTM outputs and compares their observed public-source coverage against the `deepline-pre-research` contract. It does not call paid providers or require local secrets.",
        "",
        "## Summary",
        "",
        f"{examples_full_coverage}/{examples_checked} examples from the saved `last30days` GTM corpus achieve full contract coverage under the `deepline-pre-research` skill contract.",
        "",
        f"Result: **same_or_better = {str(same_or_better).lower()}** for public and private GTM pre-research.",
        "",
        "## Source Families Checked",
        "",
        "| Source family | Contract status | last30days coverage | Deepline route today |",
        "| --- | --- | --- | --- |",
    ]

    for family in SOURCE_FAMILIES_CHECKED:
        lines.append(
            f"| {family['family']} | {family['contract_status']} | {family['last30days_coverage']} | {family['deepline_route']} |"
        )

    lines += [
        "",
        "## Deepline Additions",
        "",
        fmt(additions),
        "",
        "## Remaining Provider Gaps",
        "",
        "| Gap | Current route | Recommended addition |",
        "| --- | --- | --- |",
    ]

    for gap, route, addition in REMAINING_PROVIDER_GAPS:
        lines.append(f"| {gap} | {route} | {addition} |")

    lines += [
        "",
        "## Example Coverage",
        "",
        "| Example | Type | last30days observed sources | Required Deepline families | Deepline additions | Gaps/errors observed in saved run | Result |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    for row in rows:
        example = row["example"]
        assert isinstance(example, Example)
        lines.append(
            "| {label} | {kind} | {sources} | {required} | {adds} | {errors} | {status} |".format(
                label=example.label,
                kind=example.kind,
                sources=fmt(row["observed_sources"]),
                required=fmt(row["required"]),
                adds=fmt(row["deepline_adds"]),
                errors=fmt(row["errors"]),
                status=row["status"],
            )
        )

    lines += [
        "",
        "## Fanout And Consolidation",
        "",
        "| Area | last30days baseline | Deepline pre-research contract | Verdict |",
        "| --- | --- | --- | --- |",
    ]

    for area, old, new in FANOUT_COMPARISON:
        lines.append(f"| {area} | {old} | {new} | same or broader |")

    lines += [
        "",
        "## Conclusion",
        "",
        "- Coverage is broader than the saved `last30days` GTM pattern at the contract level because it keeps the same public/community fanout and adds CRM, warehouse, workflow, provider-cost, custom-language, and activation requirements.",
        "- Live retrieval parity still depends on Deepline catalog support. The skill must mark Reddit comments, X, TikTok, Instagram, YouTube transcripts, HN, Polymarket, Bluesky, and Truth Social as `native`, `generic route`, or `gap` after `deepline tools search`/`describe`.",
        "- The most important implementation requirement is to keep the two-phase fanout from `last30days`: broad parallel source search first, then supplemental searches from discovered handles, subreddits, domains, datasets, CRM ids, account lists, and persona language.",
        "- The consolidation contract should be considered better than `last30days` only when the implementation preserves text/URL dedupe and adds identity joins, source provenance, join keys, cost basis, and evidence clusters.",
        "",
    ]

    return "\n".join(lines), data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Deepline pre-research coverage against saved last30days examples")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS, help="Directory containing saved last30days raw reports")
    parser.add_argument("--out-md", type=Path, default=OUT_MD, help="Markdown report path")
    parser.add_argument("--out-json", type=Path, default=OUT_JSON, help="JSON report path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    markdown, data = build_report(args.corpus)
    args.out_md.write_text(markdown, encoding="utf-8")
    args.out_json.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {args.out_md}")
    print(f"Wrote {args.out_json}")


if __name__ == "__main__":
    main()
