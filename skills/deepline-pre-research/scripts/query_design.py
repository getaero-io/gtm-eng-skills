#!/usr/bin/env python3
"""Deepline pre-research query design planner.

This ports the useful query-design behavior from last30days into a standalone
Deepline helper. It does not call providers. It turns a verbose research request
into platform-specific public, private, supplemental, and custom-language query
plans that can be mapped onto Deepline tools.

Portions of the query-cleaning, query-type, source-tiering, and supplemental
entity-extraction logic are adapted from mvanhorn/last30days-skill, MIT
licensed, copyright (c) 2026 Matt Van Horn. See ../THIRD_PARTY_NOTICES.md.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any, Iterable, Literal


QueryType = Literal[
    "product",
    "concept",
    "opinion",
    "how_to",
    "comparison",
    "breaking_news",
    "prediction",
    "gtm_dataset",
    "private_workflow",
    "custom_language",
]

Depth = Literal["quick", "default", "deep"]


PREFIXES = (
    "what are the best",
    "what is the best",
    "what are the latest",
    "what are people saying about",
    "what do people think about",
    "how do i use",
    "how to use",
    "how to",
    "what are",
    "what is",
    "tips for",
    "best practices for",
)

SUFFIXES = (
    "best practices",
    "use cases",
    "prompt techniques",
    "prompting techniques",
    "prompting tips",
)

NOISE_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "and",
        "or",
        "of",
        "in",
        "on",
        "for",
        "with",
        "about",
        "to",
        "how",
        "what",
        "which",
        "who",
        "why",
        "when",
        "where",
        "does",
        "should",
        "could",
        "would",
        "best",
        "top",
        "good",
        "great",
        "awesome",
        "killer",
        "latest",
        "new",
        "news",
        "update",
        "updates",
        "trendiest",
        "trending",
        "hottest",
        "hot",
        "popular",
        "viral",
        "practices",
        "features",
        "guide",
        "tutorial",
        "recommendations",
        "advice",
        "review",
        "reviews",
        "usecases",
        "examples",
        "comparison",
        "versus",
        "vs",
        "plugin",
        "plugins",
        "skill",
        "skills",
        "tool",
        "tools",
        "prompt",
        "prompts",
        "prompting",
        "techniques",
        "tips",
        "tricks",
        "methods",
        "strategies",
        "approaches",
        "analyze",
        "analysis",
        "research",
        "data",
        "source",
        "sources",
        "public",
        "proprietary",
        "join",
        "joins",
        "using",
        "uses",
        "use",
        "people",
        "saying",
        "think",
        "said",
        "lately",
    }
)

VIDEO_NOISE_WORDS = frozenset(
    {
        "best",
        "top",
        "good",
        "great",
        "awesome",
        "killer",
        "latest",
        "new",
        "news",
        "update",
        "updates",
        "trending",
        "hottest",
        "popular",
        "viral",
        "practices",
        "features",
        "recommendations",
        "advice",
        "prompt",
        "prompts",
        "prompting",
        "methods",
        "strategies",
        "approaches",
    }
)

X_NOISE_WORDS = NOISE_WORDS | frozenset({"data", "source", "sources"})

GENERIC_HANDLES = {
    "elonmusk",
    "openai",
    "google",
    "microsoft",
    "apple",
    "meta",
    "github",
    "youtube",
    "x",
    "twitter",
    "reddit",
    "wikipedia",
    "nytimes",
    "washingtonpost",
    "cnn",
    "bbc",
    "reuters",
    "verified",
    "jack",
    "sundarpichai",
}

PRIVATE_WORKFLOW_OVERRIDE = re.compile(
    r"\b("
    r"(?:salesforce|hubspot|attio|crm).*(?:opportunit(?:y|ies)|deals?|pipeline|win-loss|forecast|stage)"
    r"|(?:opportunit(?:y|ies)|deals?|pipeline|win-loss|forecast|stage).*(?:salesforce|hubspot|attio|crm)"
    r"|crm joins?"
    r"|(?:customer match|matched audiences?|audience enrichment).*(?:b2b|paid ads|crm|personal emails?|email hashes?|match rates?)"
    r"|(?:b2b|paid ads|crm|personal emails?|email hashes?|match rates?).*(?:customer match|matched audiences?|audience enrichment)"
    r"|(?:plg|activation|churn).*(?:signal discovery|product analytics|support tickets?|onboarding events?|account firmographics)"
    r"|(?:signal discovery|product analytics|support tickets?|onboarding events?|account firmographics).*(?:plg|activation|churn)"
    r"|customer match workflow"
    r"|matched audiences?.*workflow"
    r"|workflow.*(?:personal emails?|email hashes?|match rates?)"
    r"|(?:personal emails?|email hashes?|match rates?).*workflow"
    r")\b",
    re.I,
)


PATTERNS: tuple[tuple[QueryType, re.Pattern[str]], ...] = (
    ("custom_language", re.compile(r"\b(custom language|voice of customer|pain language|messaging|copywriting|email copy|sales copy|ad copy|hooks?|objections?|cold email|talk track|positioning|follow-?up sequence|event attendee|campaign activation|buyer language)\b", re.I)),
    ("gtm_dataset", re.compile(r"\b(data sources?|datasets?|public records?|public registr(?:y|ies)|registr(?:y|ies)|licenses?|permits?|npi|provider taxonomy|taxonomy|national provider identifier|contacts?|enrichment|firmographics?|technographics?|buying signals?|intent data|waterfall|lead scoring|account scoring|predictive scoring|propensity|win-loss|match rates?|customer match|matched audiences?|paid ads|b2b|plg|saas|activation|retention|churn|signup|onboarding|partner enablement|data broker|identity verification|fraud prevention|account takeover|kyc|product launches?|launch docs?|scoring criteria|external signals?|segment analysis|icp)\b", re.I)),
    ("private_workflow", re.compile(r"\b(crm|salesforce|hubspot|attio|warehouse|data warehouse|snowflake|reverse etl|zero copy|product usage|workflow runs?|gtm workflows?|play runs?|pipeline|deal|opportunity|revops)\b", re.I)),
    ("comparison", re.compile(r"\b(vs\.?|versus|compared to|comparison|better than|difference between|switch from)\b", re.I)),
    ("how_to", re.compile(r"\b(how to|tutorial|step by step|setup|install|configure|deploy|migrate|implement|build a|create a|best practices|tips|examples|fixes?|seo fixes?|internal linking|canonical tags|noindex pruning)\b", re.I)),
    ("product", re.compile(r"\b(price|pricing|cost|buy|purchase|deal|discount|subscription|plan|tier|free tier|alternative|template|templates)\b", re.I)),
    ("opinion", re.compile(r"\b(worth it|thoughts on|opinion|review|experience with|recommend|should i|pros and cons|good or bad)\b", re.I)),
    ("prediction", re.compile(r"\b(predict|forecast|odds|chance|probability|election|outcome|bet on|market for)\b", re.I)),
    ("concept", re.compile(r"\b(what is|what are|explain|definition|how does|how do|overview|introduction|guide to|primer)\b", re.I)),
    ("breaking_news", re.compile(r"\b(latest|breaking|just announced|launched|released|new|update|news|happened|today|this week)\b", re.I)),
)

SOURCE_TIERS: dict[QueryType, dict[str, set[str]]] = {
    "product": {"tier1": {"reddit", "x", "youtube"}, "tier2": {"web", "tiktok", "instagram"}},
    "concept": {"tier1": {"reddit", "hn", "web"}, "tier2": {"youtube", "x"}},
    "opinion": {"tier1": {"reddit", "x"}, "tier2": {"youtube", "bluesky", "instagram"}},
    "how_to": {"tier1": {"youtube", "reddit", "hn"}, "tier2": {"web", "x"}},
    "comparison": {"tier1": {"reddit", "hn", "youtube"}, "tier2": {"x", "web"}},
    "breaking_news": {"tier1": {"x", "reddit", "web"}, "tier2": {"hn", "bluesky", "youtube"}},
    "prediction": {"tier1": {"polymarket", "x", "reddit"}, "tier2": {"web", "hn", "youtube"}},
    "gtm_dataset": {"tier1": {"web", "reddit", "x", "github"}, "tier2": {"youtube", "hn", "tiktok", "instagram"}},
    "private_workflow": {"tier1": {"crm", "warehouse", "workflow", "web", "reddit", "x"}, "tier2": {"github", "youtube", "hn", "tiktok", "instagram", "support"}},
    "custom_language": {"tier1": {"reddit", "x", "youtube", "crm"}, "tier2": {"tiktok", "instagram", "support", "web"}},
}

DEPTH_LIMITS: dict[Depth, dict[str, int]] = {
    "quick": {"reddit_queries": 1, "supplemental": 1, "source_tiers": 1},
    "default": {"reddit_queries": 3, "supplemental": 3, "source_tiers": 2},
    "deep": {"reddit_queries": 4, "supplemental": 5, "source_tiers": 2},
}


@dataclass(frozen=True)
class QueryVariant:
    source: str
    phase: str
    query: str
    route_hint: str
    purpose: str
    priority: int


@dataclass(frozen=True)
class QueryPlan:
    topic: str
    query_type: QueryType
    depth: Depth
    from_date: str
    to_date: str
    core_subject: str
    enabled_sources: dict[str, list[str]]
    variants: list[QueryVariant]
    supplemental_templates: list[QueryVariant]
    extraction_keys: list[str]
    scoring_notes: list[str]


def detect_query_type(topic: str) -> QueryType:
    if PRIVATE_WORKFLOW_OVERRIDE.search(topic):
        return "private_workflow"
    for query_type, pattern in PATTERNS:
        if pattern.search(topic):
            return query_type
    return "breaking_news"


def extract_core_subject(
    topic: str,
    *,
    noise: frozenset[str] | None = None,
    max_words: int | None = None,
    strip_suffixes: bool = False,
) -> str:
    text = topic.lower().strip()
    if not text:
        return text

    for prefix in PREFIXES:
        if text.startswith(prefix + " "):
            text = text[len(prefix) :].strip()
            break

    if strip_suffixes:
        for suffix in SUFFIXES:
            if text.endswith(" " + suffix):
                text = text[: -len(suffix)].strip()
                break

    words = re.findall(r"[a-z0-9][a-z0-9+._/-]*", text)
    noise_set = noise if noise is not None else NOISE_WORDS
    filtered = [word for word in words if word not in noise_set]
    if max_words and filtered:
        filtered = filtered[:max_words]

    result = " ".join(filtered) if filtered else text
    return result.rstrip("?!.") if not max_words else (result or topic.lower().strip())


def extract_compound_terms(topic: str) -> list[str]:
    terms: list[str] = []
    for match in re.finditer(r"\b\w+-\w+(?:-\w+)*\b", topic):
        terms.append(match.group())
    for match in re.finditer(r"(?:[A-Z][a-z0-9]+\s+){1,}[A-Z][a-z0-9]+", topic):
        terms.append(match.group())
    return dedupe_keep_order(terms)


def dedupe_keep_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        key = value.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(value.strip())
    return out


def source_tiers(query_type: QueryType, depth: Depth, explicit_sources: set[str] | None = None) -> dict[str, list[str]]:
    tiers = SOURCE_TIERS[query_type]
    enabled: dict[str, list[str]] = {"tier1": sorted(tiers["tier1"]), "tier2": [], "explicit": []}
    if DEPTH_LIMITS[depth]["source_tiers"] >= 2:
        enabled["tier2"] = sorted(tiers["tier2"])
    if explicit_sources:
        already = set(enabled["tier1"]) | set(enabled["tier2"])
        enabled["explicit"] = sorted(explicit_sources - already)
    return enabled


def reddit_queries(topic: str, query_type: QueryType, depth: Depth) -> list[QueryVariant]:
    core = extract_core_subject(topic)
    original = topic.strip().rstrip("?!.")
    queries = [core]
    if core.lower() != original.lower() and len(original.split()) <= 8:
        queries.append(original)
    if depth in ("default", "deep") and query_type in ("product", "opinion", "gtm_dataset", "custom_language"):
        queries.append(f"{core} worth it OR thoughts OR review")
    if depth == "deep" and query_type in ("product", "opinion", "how_to", "gtm_dataset", "private_workflow"):
        queries.append(f"{core} issues OR problems OR broken")

    return [
        QueryVariant(
            "reddit",
            "broad",
            query,
            "Reddit native/ScrapeCreators if available; otherwise vetted generic route",
            "Global Reddit discovery; first query relevance sort, later variants top/new",
            idx + 1,
        )
        for idx, query in enumerate(dedupe_keep_order(queries)[: DEPTH_LIMITS[depth]["reddit_queries"]])
    ]


def x_queries(topic: str, from_date: str) -> list[QueryVariant]:
    core = extract_core_subject(topic, noise=X_NOISE_WORDS, max_words=5, strip_suffixes=True)
    variants = [
        QueryVariant("x", "broad", f"{core} since:{from_date}", "X native/BYOK or managed provider", "Literal keyword search with recency filter", 1)
    ]
    compounds = extract_compound_terms(topic)
    if compounds:
        or_parts = " OR ".join(f'"{term}"' for term in compounds[:3])
        variants.append(QueryVariant("x", "fallback", f"({or_parts}) since:{from_date}", "X native/BYOK or managed provider", "Fallback for named multi-word or hyphenated terms", 2))
    words = core.split()
    if len(words) > 2:
        variants.append(QueryVariant("x", "fallback", f"{' '.join(words[:2])} since:{from_date}", "X native/BYOK or managed provider", "Fallback with fewer ANDed keywords", 3))
    if words:
        strongest = max([w for w in words if w not in NOISE_WORDS] or words, key=len)
        variants.append(QueryVariant("x", "fallback", f"{strongest} since:{from_date}", "X native/BYOK or managed provider", "Last-chance strongest-token fallback", 4))
    return variants


def video_queries(topic: str, source: str) -> list[QueryVariant]:
    core = extract_core_subject(topic, noise=VIDEO_NOISE_WORDS)
    return [
        QueryVariant(source, "broad", core, f"{source} transcript/caption route", "Search captions, transcripts, and creator metadata", 1),
        QueryVariant(source, "fallback", f"{core} tutorial OR review OR tips", f"{source} transcript/caption route", "Content-type fallback for explainers and reviews", 2),
    ]


def web_queries(topic: str, query_type: QueryType) -> list[QueryVariant]:
    core = extract_core_subject(topic)
    variants = [
        QueryVariant("web", "broad", topic.strip(), "Serper/Exa/Parallel search; Firecrawl for extraction", "High-recall web discovery", 1),
        QueryVariant("web", "fallback", f'"{core}"', "Serper/Exa/Parallel search", "Exact core-subject search", 2),
    ]
    if query_type in ("gtm_dataset", "private_workflow"):
        variants.extend(
            [
                QueryVariant("web", "dataset", f'{core} dataset OR API OR csv OR "public records"', "Serper/Exa/Parallel search", "Find materializable datasets and APIs", 3),
                QueryVariant("github", "dataset", f'{core} site:github.com dataset OR api OR csv', "Web/GitHub search", "Find repos, scripts, and data dictionaries", 4),
            ]
        )
    return variants


def private_queries(topic: str) -> list[QueryVariant]:
    core = extract_core_subject(topic)
    return [
        QueryVariant("crm", "private", core, "salesforce/hubspot/attio describe then scoped query", "Find account/contact/deal fields and recent records", 1),
        QueryVariant("warehouse", "private", core, "semantic layer first, then scoped warehouse query", "Find metrics, dimensions, and product/customer evidence", 2),
        QueryVariant("workflow", "private", core, "plays/workflow/session/run tools", "Find run ids, outputs, failures, usage, and activation paths", 3),
        QueryVariant("support", "private", core, "CRM notes, docs, Slack, call transcript connectors", "Find customer wording, objections, and support pain", 4),
    ]


def custom_language_queries(topic: str) -> list[QueryVariant]:
    core = extract_core_subject(topic)
    return [
        QueryVariant("custom_language", "language", f"{core} pain OR objection OR frustrated OR switched", "Social/community plus CRM/support/call sources", "Mine pain and objection language", 1),
        QueryVariant("custom_language", "language", f"{core} alternatives OR competitor OR pricing OR migration", "Social/community plus competitor pages", "Mine competitor and category language", 2),
        QueryVariant("custom_language", "language", f"{core} subject line OR cold email OR hook OR opener", "Web/social plus campaign history", "Mine outbound language patterns", 3),
    ]


def supplemental_templates(from_date: str, depth: Depth) -> list[QueryVariant]:
    cap = DEPTH_LIMITS[depth]["supplemental"]
    templates = [
        QueryVariant("reddit", "supplemental", "r/{subreddit} {core_subject}", "Reddit subreddit search", "Drill into discovered or user-provided communities", 1),
        QueryVariant("x", "supplemental", "from:{handle} {core_subject} since:" + from_date, "X handle search", "Drill into discovered topic-specific handles", 2),
        QueryVariant("x", "supplemental", "from:{resolved_handle} since:" + from_date, "X unfiltered handle search", "Resolved entity handle; do not require topic words", 3),
        QueryVariant("web", "supplemental", "site:{domain} {core_subject}", "Web extraction/search", "Drill into discovered domains and docs", 4),
        QueryVariant("company", "supplemental", "{domain_or_linkedin_url}", "Company/account providers", "Resolve account identities from discovered domains", 5),
        QueryVariant("person", "supplemental", "{company_domain} {title_or_persona}", "People/contact providers", "Find decision makers after account qualification", 6),
        QueryVariant("crm", "supplemental", "{crm_object_id} OR {domain} OR {email}", "Private connector", "Join public evidence to CRM records", 7),
        QueryVariant("dataset", "supplemental", "{agency_or_repo_or_api_name} {dataset_id}", "Web/API/GitHub route", "Materialize dataset leads", 8),
        QueryVariant("custom_language", "supplemental", '"{exact_phrase}" {persona_or_segment}', "Social/private language sources", "Cluster exact phrases by persona and use case", 9),
    ]
    return templates[: max(cap + 4, 5)]


def extraction_keys(query_type: QueryType) -> list[str]:
    keys = [
        "subreddits",
        "handles",
        "hashtags",
        "domains",
        "urls",
        "company_names",
        "linkedin_urls",
        "dataset_or_api_names",
    ]
    if query_type in ("private_workflow", "custom_language"):
        keys.extend(["crm_object_ids", "deal_or_opportunity_ids", "workflow_run_ids", "support_ticket_ids"])
    if query_type in ("custom_language", "gtm_dataset"):
        keys.extend(["personas", "pain_phrases", "objections", "competitor_names", "category_terms"])
    return keys


def scoring_notes(query_type: QueryType) -> list[str]:
    notes = ["score relevance, recency, engagement, and source quality before synthesis"]
    if query_type in ("gtm_dataset", "private_workflow"):
        notes.extend(["boost materializable datasets/APIs", "boost records with stable join keys", "penalize cost-unknown full-scope plans"])
    if query_type in ("private_workflow", "custom_language"):
        notes.extend(["boost private evidence tied to CRM outcome or workflow usage", "keep private provenance separate from public citations"])
    if query_type == "custom_language":
        notes.extend(["separate exact quotes from rewritten copy", "cluster by persona, pain, objection, and reuse field"])
    return notes


def build_query_plan(
    topic: str,
    *,
    depth: Depth = "default",
    from_date: str | None = None,
    to_date: str | None = None,
    explicit_sources: set[str] | None = None,
) -> QueryPlan:
    today = date.today()
    to_date = to_date or today.isoformat()
    from_date = from_date or (today - timedelta(days=30)).isoformat()
    query_type = detect_query_type(topic)
    tiers = source_tiers(query_type, depth, explicit_sources=explicit_sources)
    selected_sources = set(tiers["tier1"]) | set(tiers["tier2"]) | set(tiers["explicit"])

    variants: list[QueryVariant] = []
    if "reddit" in selected_sources:
        variants.extend(reddit_queries(topic, query_type, depth))
    if "x" in selected_sources:
        variants.extend(x_queries(topic, from_date))
    for source in ("youtube", "tiktok", "instagram"):
        if source in selected_sources:
            variants.extend(video_queries(topic, source))
    if "web" in selected_sources or "github" in selected_sources:
        variants.extend(web_queries(topic, query_type))
    if selected_sources & {"crm", "warehouse", "workflow", "support"}:
        variants.extend(private_queries(topic))
    if query_type == "custom_language":
        variants.extend(custom_language_queries(topic))
    if "hn" in selected_sources:
        variants.append(QueryVariant("hn", "broad", extract_core_subject(topic), "Hacker News Algolia or web fallback", "Technical/community discussion search", 1))
    if "polymarket" in selected_sources:
        variants.append(QueryVariant("polymarket", "broad", extract_core_subject(topic), "Polymarket Gamma or web fallback", "Prediction-market discovery", 1))
    if "bluesky" in selected_sources:
        variants.append(QueryVariant("bluesky", "broad", extract_core_subject(topic, max_words=5), "Bluesky API/BYOK route", "Public social post search", 1))

    return QueryPlan(
        topic=topic,
        query_type=query_type,
        depth=depth,
        from_date=from_date,
        to_date=to_date,
        core_subject=extract_core_subject(topic),
        enabled_sources=tiers,
        variants=variants,
        supplemental_templates=supplemental_templates(from_date, depth),
        extraction_keys=extraction_keys(query_type),
        scoring_notes=scoring_notes(query_type),
    )


def extract_entities_for_supplemental(items: list[dict[str, Any]], limit: int = 5) -> dict[str, list[str]]:
    counts: dict[str, dict[str, int]] = {"handles": {}, "hashtags": {}, "subreddits": {}, "domains": {}}
    for item in items:
        text = " ".join(str(item.get(k, "")) for k in ("text", "title", "excerpt", "url"))
        for handle in re.findall(r"@(\w{1,15})", text):
            key = handle.lower()
            if key not in GENERIC_HANDLES:
                counts["handles"][key] = counts["handles"].get(key, 0) + 1
        for hashtag in re.findall(r"#(\w{2,30})", text):
            key = "#" + hashtag.lower()
            counts["hashtags"][key] = counts["hashtags"].get(key, 0) + 1
        for sub in re.findall(r"(?:^|\W)r/(\w{2,30})", text):
            counts["subreddits"][sub] = counts["subreddits"].get(sub, 0) + 1
        for domain in re.findall(r"https?://(?:www\.)?([^/\s)]+)", text):
            counts["domains"][domain.lower()] = counts["domains"].get(domain.lower(), 0) + 1

    return {
        name: [value for value, _ in sorted(values.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]]
        for name, values in counts.items()
    }


def plan_to_dict(plan: QueryPlan) -> dict[str, Any]:
    data = asdict(plan)
    data["variants"] = [asdict(v) for v in plan.variants]
    data["supplemental_templates"] = [asdict(v) for v in plan.supplemental_templates]
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Deepline pre-research query plan")
    parser.add_argument("topic", nargs="+")
    parser.add_argument("--depth", choices=["quick", "default", "deep"], default="default")
    parser.add_argument("--from-date")
    parser.add_argument("--to-date")
    parser.add_argument("--sources", help="Comma-separated explicit sources to include")
    args = parser.parse_args()

    explicit = {s.strip().lower() for s in args.sources.split(",")} if args.sources else None
    plan = build_query_plan(
        " ".join(args.topic),
        depth=args.depth,
        from_date=args.from_date,
        to_date=args.to_date,
        explicit_sources=explicit,
    )
    print(json.dumps(plan_to_dict(plan), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
