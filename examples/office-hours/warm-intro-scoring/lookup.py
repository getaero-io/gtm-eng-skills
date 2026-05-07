"""CLI lookup interface for warm intro system."""
import argparse
import sys
from typing import Optional

from .db import WarmIntroDB
from .models import WarmIntroMatch
from .scorer import WarmIntroScorer
from .appearances import AppearanceDiscoverer


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
        "-p", "--platforms",
        nargs="+",
        help="Target platforms to match against (e.g., 'Sales Hacker Podcast')",
    )
    parser.add_argument(
        "--db",
        help="Path to database file (default: data/warm_intros.db)",
    )

    args = parser.parse_args()

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
        print(f"Database: {total_contacts} contacts ({enriched_contacts} enriched)")

        # Build target_platforms list
        target_platforms = args.platforms or []

        # If target_name provided, search for their appearances
        if args.target_name:
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
                print(f"Found {len(search_results)} appearances")
            else:
                print(
                    "No appearances found via search. "
                    "Use --platforms to specify platforms manually."
                )

        if target_platforms:
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

        # Print results
        lookup.print_results(matches)

    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
