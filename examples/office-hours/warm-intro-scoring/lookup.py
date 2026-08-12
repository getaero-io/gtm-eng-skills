"""CLI lookup interface for warm intro system."""
import argparse
import csv
import sys
from pathlib import Path
from typing import Optional, Sequence, TextIO

from .db import WarmIntroDB
from .models import WarmIntroMatch
from .scorer import WarmIntroScorer

_OFFICE_HOURS_DIR = Path(__file__).resolve().parent.parent
if str(_OFFICE_HOURS_DIR) not in sys.path:
    sys.path.insert(0, str(_OFFICE_HOURS_DIR))

from warm_intro_contract import build_path_id  # noqa: E402

try:
    from .appearances import AppearanceDiscoverer
except ModuleNotFoundError as error:
    if error.name != f"{__package__}.appearances":
        raise

    class AppearanceDiscoverer:  # type: ignore[no-redef]
        """No-network fallback for this standalone office-hours example."""

        def __init__(self, db: WarmIntroDB):
            self.db = db

        def search_appearances(
            self,
            name: str,
            company: Optional[str] = None,
        ) -> list[dict[str, str]]:
            return []


def format_match(match: WarmIntroMatch, rank: int) -> str:
    """Format a match for CLI output.

    Args:
        match: The warm intro match to format
        rank: The rank number (1-indexed)

    Returns:
        Formatted string for CLI display
    """
    contact = match.contact
    lines = []

    # Header with rank, name, and score
    lines.append(f"#{rank} {contact.full_name} (Score: {match.score:.1f})")
    lines.append("-" * 50)

    # Current position and company
    if contact.current_position and contact.current_company:
        lines.append(f"  Position: {contact.current_position} at {contact.current_company}")
    elif contact.current_position:
        lines.append(f"  Position: {contact.current_position}")
    elif contact.current_company:
        lines.append(f"  Company: {contact.current_company}")

    # Headline
    if contact.headline:
        lines.append(f"  Headline: {contact.headline}")

    # Connected date
    if contact.connected_on:
        lines.append(f"  Connected: {contact.connected_on.isoformat()}")

    # LinkedIn URL
    lines.append(f"  LinkedIn: {contact.linkedin_url}")

    # Email
    if contact.email:
        lines.append(f"  Email: {contact.email}")
    else:
        lines.append("  Email: N/A")

    # Why this intro section
    if match.reasons:
        lines.append("")
        lines.append("  Why this intro:")
        for reason in match.reasons:
            lines.append(f"    - {reason}")

    # Shared companies
    if match.shared_companies:
        lines.append("")
        lines.append(f"  Shared companies: {', '.join(match.shared_companies)}")

    # Shared schools
    if match.shared_schools:
        lines.append("")
        lines.append(f"  Shared schools: {', '.join(match.shared_schools)}")

    # Shared appearances
    if match.shared_appearances:
        lines.append("")
        lines.append(f"  Shared appearances: {', '.join(match.shared_appearances)}")

    lines.append("")  # Blank line between matches
    return "\n".join(lines)


class WarmIntroLookup:
    """Lookup interface for finding warm intro matches."""

    CSV_FIELDNAMES = (
        "campaign_id",
        "owner_id",
        "connector_id",
        "target_id",
        "path_id",
        "connector_name",
        "connector_linkedin",
        "connector_company",
        "target_name",
        "target_title",
        "target_company",
        "shared_signal",
        "shared_detail",
        "relationship_confidence",
        "direct_intro_score",
        "work_overlap_score",
        "relationship_score",
        "school_city_community_score",
        "role_industry_score",
        "investor_score",
        "total_score",
        "segment",
        "reviewed_override",
        "evidence_ids",
    )

    def __init__(self, db: WarmIntroDB):
        """Initialize with database connection.

        Args:
            db: WarmIntroDB instance
        """
        self.db = db
        self.scorer = WarmIntroScorer(db)

    def search(
        self,
        company: Optional[str] = None,
        school: Optional[str] = None,
        role: Optional[str] = None,
        target_platforms: Optional[list[str]] = None,
        limit: int = 20,
    ) -> list[WarmIntroMatch]:
        """Search for warm intro matches.

        Args:
            company: Target company name
            school: Target school name
            role: Target role/position
            target_platforms: List of platforms the target appeared on
            limit: Maximum number of results

        Returns:
            List of WarmIntroMatch objects sorted by score descending

        Raises:
            ValueError: If no search criteria provided
        """
        if not any([company, school, role, target_platforms]):
            raise ValueError(
                "At least one of company, school, role, or target_platforms must be provided"
            )

        return self.scorer.find_matches(
            target_company=company,
            target_school=school,
            target_role=role,
            target_platforms=target_platforms,
            limit=limit,
        )

    def print_results(self, matches: list[WarmIntroMatch]) -> None:
        """Print formatted results to stdout.

        Args:
            matches: List of WarmIntroMatch objects to display
        """
        if not matches:
            print("No matches found.")
            return

        print(f"\nFound {len(matches)} match(es):\n")
        for i, match in enumerate(matches, 1):
            print(format_match(match, rank=i))

    def export_csv(
        self,
        matches: Sequence[WarmIntroMatch],
        output: TextIO,
        target_name: str,
        target_title: str,
        target_company: str,
        campaign_id: str,
        owner_id: str,
        target_id: str,
    ) -> None:
        """Write deterministic, ask-thread-ready path rows."""
        writer = csv.DictWriter(
            output,
            fieldnames=self.CSV_FIELDNAMES,
            lineterminator="\n",
        )
        writer.writeheader()
        ordered_matches = sorted(
            matches,
            key=lambda match: (
                -match.total_score,
                " ".join(match.contact.full_name.casefold().split()),
                match.contact.id,
            ),
        )
        for match in ordered_matches:
            path_id = build_path_id(
                campaign_id,
                owner_id,
                match.contact.id,
                target_id,
            )
            writer.writerow(
                {
                    "campaign_id": campaign_id,
                    "owner_id": owner_id,
                    "connector_id": match.contact.id,
                    "target_id": target_id,
                    "path_id": path_id,
                    "connector_name": match.contact.full_name,
                    "connector_linkedin": match.contact.linkedin_url,
                    "connector_company": match.contact.current_company or "",
                    "target_name": target_name or match.target_name,
                    "target_title": target_title or match.target_title,
                    "target_company": target_company or match.target_company,
                    "shared_signal": match.shared_signal,
                    "shared_detail": match.shared_detail,
                    "relationship_confidence": match.relationship_confidence,
                    "direct_intro_score": match.direct_intro_score,
                    "work_overlap_score": match.work_overlap_score,
                    "relationship_score": match.relationship_score,
                    "school_city_community_score": match.school_city_community_score,
                    "role_industry_score": match.role_industry_score,
                    "investor_score": match.investor_score,
                    "total_score": match.total_score,
                    "segment": match.segment,
                    "reviewed_override": "false",
                    "evidence_ids": ";".join(sorted(set(match.evidence_ids))),
                }
            )


def main() -> int:
    """CLI entry point for warm intro lookup.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description="Find warm intro connections based on company, school, or role"
    )
    parser.add_argument(
        "-c", "--company",
        help="Target company name to search for",
    )
    parser.add_argument(
        "-s", "--school",
        help="Target school name to search for",
    )
    parser.add_argument(
        "-r", "--role",
        help="Target role/position to search for",
    )
    parser.add_argument(
        "-n", "--limit",
        type=int,
        default=20,
        help="Maximum number of results (default: 20)",
    )
    parser.add_argument(
        "-t", "--target-name",
        help="Target person name to look up their appearances for matching",
    )
    parser.add_argument(
        "--target-title",
        help="Target person's current title for CSV output",
    )
    parser.add_argument("--campaign-id", help="Campaign namespace required for CSV export")
    parser.add_argument("--owner-id", help="Campaign owner namespace required for CSV export")
    parser.add_argument("--target-id", help="Stable target contact ID required for CSV export")
    parser.add_argument(
        "-p", "--platforms",
        nargs="+",
        help="Target platforms to match against (e.g., 'Sales Hacker Podcast')",
    )
    parser.add_argument(
        "--db",
        help="Path to database file (default: data/warm_intros.db)",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        help="Write deterministic warm-path rows to this CSV file",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress human-readable terminal output",
    )

    args = parser.parse_args()

    if args.csv and not all((args.campaign_id, args.owner_id, args.target_id)):
        parser.error("--csv requires --campaign-id, --owner-id, and --target-id")

    # Validate at least one search criteria
    if not any([args.company, args.school, args.role, args.target_name, args.platforms]):
        parser.error(
            "At least one of --company, --school, --role, --target-name, or --platforms is required"
        )

    # Initialize database
    db = WarmIntroDB(args.db)
    try:
        db.init()

        # Print database stats
        total_contacts = db.get_contact_count()
        enriched_contacts = db.get_enriched_count()
        if not args.quiet:
            print(f"Database: {total_contacts} contacts ({enriched_contacts} enriched)")

        # Build target_platforms list
        target_platforms = args.platforms or []

        # If target_name provided, search for their appearances
        if args.target_name:
            if not args.quiet:
                print(f"\nSearching for appearances of: {args.target_name}")
            discoverer = AppearanceDiscoverer(db)
            # Note: search_appearances returns empty list (stub)
            # In production, this would search the web for appearances
            search_results = discoverer.search_appearances(
                name=args.target_name, company=args.company
            )
            if search_results:
                for result in search_results:
                    platform = result.get("platform")
                    if platform and platform not in target_platforms:
                        target_platforms.append(platform)
                if not args.quiet:
                    print(f"Found {len(search_results)} appearances")
            elif not args.quiet:
                print(
                    "No appearances found via search. "
                    "Use --platforms to specify platforms manually."
                )

        if target_platforms and not args.quiet:
            print(f"Target platforms: {', '.join(target_platforms)}")

        # Search
        lookup = WarmIntroLookup(db)
        matches = lookup.search(
            company=args.company,
            school=args.school,
            role=args.role,
            target_platforms=target_platforms if target_platforms else None,
            limit=args.limit,
        )

        if args.csv:
            with args.csv.open("w", encoding="utf-8", newline="") as output:
                lookup.export_csv(
                    matches,
                    output,
                    target_name=args.target_name or "",
                    target_title=args.target_title or "",
                    target_company=args.company or "",
                    campaign_id=args.campaign_id,
                    owner_id=args.owner_id,
                    target_id=args.target_id,
                )

        # CSV export supplements terminal results unless quiet mode is explicit.
        if not args.quiet:
            lookup.print_results(matches)

    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
