"""Apify LinkedIn profile enrichment for warm intro system."""
import argparse
import os
import time
import uuid
from datetime import date, datetime, timezone
from typing import Optional

import requests

from .db import WarmIntroDB
from .models import Contact, Experience, Education


class ApifyEnricher:
    """Enriches contacts with LinkedIn profile data via Apify."""

    ACTOR_ID = "dev_fusion~Linkedin-Profile-Scraper"

    def __init__(
        self,
        apify_token: Optional[str] = None,
        db: Optional[WarmIntroDB] = None,
        batch_size: int = 25,
        poll_interval: int = 10
    ):
        self.apify_token = apify_token or os.environ.get("APIFY_TOKEN")
        self.db = db
        self.batch_size = batch_size
        self.poll_interval = poll_interval

    def parse_experiences(self, contact_id: str, profile: dict) -> list[Experience]:
        """Extract work history from Apify response (dev_fusion actor schema)."""
        experiences = []
        # dev_fusion actor uses "experiences" with jobStartedOn/jobEndedOn/jobStillWorking
        items = profile.get("experiences") or profile.get("positions") or []

        for pos in items:
            company_name = pos.get("companyName")
            if not company_name:
                continue

            # dev_fusion: jobStartedOn / jobEndedOn; fallback to startDate / endDate
            start_date = self._parse_date(
                pos.get("jobStartedOn") or pos.get("startDate")
            )
            end_date = self._parse_date(
                pos.get("jobEndedOn") or pos.get("endDate")
            )
            is_current = bool(
                pos.get("jobStillWorking") or pos.get("current") or (end_date is None and start_date is not None)
            )

            exp = Experience(
                id=str(uuid.uuid4()),
                contact_id=contact_id,
                company_name=company_name,
                # dev_fusion: companyLink1; fallback to companyUrl
                company_linkedin_url=pos.get("companyLink1") or pos.get("companyUrl"),
                title=pos.get("title", ""),
                description=pos.get("jobDescription") or pos.get("description"),
                location=pos.get("jobLocation") or pos.get("location"),
                start_date=start_date,
                end_date=end_date,
                is_current=is_current,
            )
            experiences.append(exp)

        return experiences

    def parse_educations(self, contact_id: str, profile: dict) -> list[Education]:
        """Extract education from Apify response (dev_fusion actor schema)."""
        educations = []
        # dev_fusion uses "educations"; fallback to "schools"
        items = profile.get("educations") or profile.get("schools") or []

        for school in items:
            school_name = school.get("schoolName")
            if not school_name:
                continue

            edu = Education(
                id=str(uuid.uuid4()),
                contact_id=contact_id,
                school_name=school_name,
                school_linkedin_url=school.get("schoolLink") or school.get("schoolUrl"),
                degree=school.get("degree"),
                field_of_study=school.get("fieldOfStudy"),
                start_year=school.get("startYear"),
                end_year=school.get("endYear"),
            )
            educations.append(edu)

        return educations

    def store_enrichment(self, contact_id: str, profile: dict) -> None:
        """Update contact with enrichment data and store experiences/educations.

        Deletes existing experiences and educations before inserting new ones.

        Args:
            contact_id: The contact ID to update.
            profile: The Apify profile response dict.
        """
        if not self.db or not self.db.conn:
            raise ValueError("Database not initialized")

        now = datetime.now(timezone.utc).isoformat()

        # Update contact headline, location, and enriched_at
        self.db.conn.execute("""
            UPDATE contacts
            SET headline = COALESCE(?, headline),
                location = COALESCE(?, location),
                enriched_at = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            profile.get("headline"),
            profile.get("location"),
            now,
            now,
            contact_id
        ))

        # Delete old experiences and educations
        self.db.conn.execute("DELETE FROM experiences WHERE contact_id = ?", (contact_id,))
        self.db.conn.execute("DELETE FROM educations WHERE contact_id = ?", (contact_id,))

        # Parse and insert new experiences
        experiences = self.parse_experiences(contact_id, profile)
        for exp in experiences:
            self.db.insert_experience(exp)

        # Parse and insert new educations
        educations = self.parse_educations(contact_id, profile)
        for edu in educations:
            self.db.insert_education(edu)

        self.db.conn.commit()

    def call_apify(self, profile_urls: list[str]) -> list[dict]:
        """Call Apify actor to scrape LinkedIn profiles.

        Args:
            profile_urls: List of LinkedIn profile URLs to scrape.

        Returns:
            List of profile dicts from Apify.
        """
        if not self.apify_token:
            raise ValueError("Apify token not provided")

        if not profile_urls:
            return []

        # Start the actor run
        run_url = f"https://api.apify.com/v2/acts/{self.ACTOR_ID}/runs"
        headers = {"Authorization": f"Bearer {self.apify_token}"}
        payload = {
            "profileUrls": profile_urls
        }

        try:
            response = requests.post(run_url, json=payload, headers=headers, timeout=60)

            if response.status_code != 201:
                print(f"Apify API error: {response.status_code} - {response.text}")
                return []

            run_data = response.json()
            run_id = run_data.get("data", {}).get("id")

            if not run_id:
                print("No run ID returned from Apify")
                return []

            # Poll until complete (max 30 minutes)
            status_url = f"https://api.apify.com/v2/actor-runs/{run_id}"
            max_polls = 180  # 30 min at 10-second intervals
            poll_count = 0
            while poll_count < max_polls:
                poll_count += 1
                status_response = requests.get(status_url, headers=headers, timeout=30)
                if status_response.status_code != 200:
                    print(f"Failed to get run status: {status_response.status_code}")
                    return []

                status_data = status_response.json()
                status = status_data.get("data", {}).get("status")

                if status == "SUCCEEDED":
                    break
                elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
                    print(f"Apify run failed with status: {status}")
                    return []

                time.sleep(self.poll_interval)

            if poll_count >= max_polls:
                print("Apify run timed out after 30 minutes")
                return []

            # Fetch results from default dataset
            dataset_id = status_data.get("data", {}).get("defaultDatasetId")
            if not dataset_id:
                print("No dataset ID in run result")
                return []

            items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items"
            items_response = requests.get(items_url, headers=headers, timeout=60)

            if items_response.status_code != 200:
                print(f"Failed to fetch dataset items: {items_response.status_code}")
                return []

            return items_response.json()

        except requests.RequestException as e:
            print(f"Request error: {e}")
            return []

    def enrich_batch(self, contacts: list[Contact]) -> int:
        """Enrich a batch of contacts.

        Args:
            contacts: List of Contact objects to enrich.

        Returns:
            Number of contacts successfully enriched.
        """
        if not contacts:
            return 0

        profile_urls = [c.linkedin_url for c in contacts]
        results = self.call_apify(profile_urls)

        if not results:
            return 0

        # Build a map of URL to profile for matching
        url_to_profile = {}
        for profile in results:
            # dev_fusion actor returns "linkedinUrl"; fallback to url/profileUrl
            profile_url = (
                profile.get("linkedinUrl")
                or profile.get("linkedinPublicUrl")
                or profile.get("url")
                or profile.get("profileUrl")
            )
            if profile_url:
                normalized = profile_url.rstrip("/").lower()
                url_to_profile[normalized] = profile

        enriched_count = 0
        for contact in contacts:
            normalized_contact_url = contact.linkedin_url.rstrip("/").lower()

            # Try to find matching profile
            profile = url_to_profile.get(normalized_contact_url)

            if profile:
                self.store_enrichment(contact.id, profile)
                enriched_count += 1
            else:
                # If no URL match, try by name as fallback
                for profile in results:
                    full_name = profile.get("fullName", "").lower()
                    contact_name = f"{contact.first_name} {contact.last_name}".lower()
                    if full_name == contact_name:
                        self.store_enrichment(contact.id, profile)
                        enriched_count += 1
                        break

        return enriched_count

    def run(self, limit: Optional[int] = None) -> int:
        """Main enrichment loop.

        Fetches unenriched contacts and processes them in batches.

        Args:
            limit: Maximum number of contacts to enrich.

        Returns:
            Total number of contacts enriched.
        """
        if not self.db:
            raise ValueError("Database not provided")

        total_enriched = 0
        remaining = limit

        while True:
            # Determine batch size
            fetch_limit = self.batch_size
            if remaining is not None:
                fetch_limit = min(self.batch_size, remaining)

            contacts = self.db.get_unenriched_contacts(limit=fetch_limit)

            if not contacts:
                break

            enriched = self.enrich_batch(contacts)
            total_enriched += enriched

            if remaining is not None:
                remaining -= len(contacts)
                if remaining <= 0:
                    break

        return total_enriched

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string from Apify (YYYY-MM or YYYY format).

        Args:
            date_str: Date string like "2023-01" or "2023".

        Returns:
            date object or None.
        """
        if not date_str:
            return None

        try:
            # Try YYYY-MM format
            if "-" in date_str:
                parts = date_str.split("-")
                year = int(parts[0])
                month = int(parts[1]) if len(parts) > 1 else 1
                return date(year, month, 1)
            else:
                # Just YYYY
                return date(int(date_str), 1, 1)
        except (ValueError, IndexError):
            return None


def main():
    """CLI entry point for LinkedIn enrichment."""
    parser = argparse.ArgumentParser(
        description="Enrich LinkedIn contacts via Apify"
    )
    parser.add_argument(
        "--token",
        dest="apify_token",
        help="Apify API token (default: APIFY_TOKEN env var)"
    )
    parser.add_argument(
        "--db",
        dest="db_path",
        help="Path to SQLite database (default: data/warm_intros.db)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of contacts to enrich"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=25,
        help="Number of profiles per Apify batch (default: 25)"
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=10,
        help="Seconds between status checks (default: 10)"
    )

    args = parser.parse_args()

    db = WarmIntroDB(args.db_path)
    db.init()

    try:
        enricher = ApifyEnricher(
            apify_token=args.apify_token,
            db=db,
            batch_size=args.batch_size,
            poll_interval=args.poll_interval
        )
        count = enricher.run(limit=args.limit)
        print(f"Enriched {count} contacts")
    finally:
        db.close()


if __name__ == "__main__":
    main()
