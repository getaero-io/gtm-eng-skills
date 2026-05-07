"""LinkedIn CSV export ingestion for warm intro system."""
import argparse
import csv
import uuid
from datetime import datetime
from typing import Optional

from .db import WarmIntroDB
from .models import Contact


class LinkedInIngester:
    """Ingests LinkedIn CSV exports into the warm intro database."""

    def __init__(self, csv_path: str, db: Optional[WarmIntroDB] = None):
        self.csv_path = csv_path
        self.db = db

    def parse_csv(self) -> list[Contact]:
        """Parse CSV file, skipping notes header until 'First Name,' line.

        Returns list of Contact objects.
        """
        contacts = []

        with open(self.csv_path, 'r', encoding='utf-8') as f:
            # Skip lines until we find the header row
            header_line = None
            for line in f:
                if line.startswith('First Name,'):
                    header_line = line
                    break

            if not header_line:
                return contacts

            # Reset and read with DictReader from this point
            # We need to combine the header with remaining lines
            remaining_content = header_line + f.read()

        # Parse as CSV using DictReader
        from io import StringIO
        reader = csv.DictReader(StringIO(remaining_content))

        for row in reader:
            contact = self._parse_row(row)
            if contact:
                contacts.append(contact)

        return contacts

    def _parse_row(self, row: dict) -> Optional[Contact]:
        """Parse a single CSV row into a Contact.

        Returns None if required fields are missing.
        """
        first_name = row.get('First Name', '').strip()
        last_name = row.get('Last Name', '').strip()
        linkedin_url = row.get('URL', '').strip()

        # Required fields
        if not first_name or not last_name or not linkedin_url:
            return None

        # Optional fields
        email = row.get('Email Address', '').strip() or None
        company = row.get('Company', '').strip() or None
        position = row.get('Position', '').strip() or None
        connected_on_str = row.get('Connected On', '').strip()

        # Parse date in format "10 Apr 2026"
        connected_on = None
        if connected_on_str:
            try:
                connected_on = datetime.strptime(connected_on_str, '%d %b %Y').date()
            except ValueError:
                pass

        return Contact(
            id=str(uuid.uuid4()),
            first_name=first_name,
            last_name=last_name,
            linkedin_url=linkedin_url,
            email=email,
            current_company=company,
            current_position=position,
            connected_on=connected_on
        )

    def ingest(self) -> int:
        """Parse CSV and store all contacts in database.

        Returns count of contacts ingested.
        """
        contacts = self.parse_csv()

        if not self.db:
            raise ValueError("Database not provided")

        for contact in contacts:
            self.db.insert_contact(contact)

        return len(contacts)


def main():
    """CLI entry point for LinkedIn CSV ingestion."""
    parser = argparse.ArgumentParser(
        description='Ingest LinkedIn CSV export into warm intro database'
    )
    parser.add_argument(
        'csv_path',
        help='Path to LinkedIn CSV export file'
    )
    parser.add_argument(
        '--db',
        dest='db_path',
        help='Path to SQLite database (default: data/warm_intros.db)'
    )

    args = parser.parse_args()

    db = WarmIntroDB(args.db_path)
    db.init()

    try:
        ingester = LinkedInIngester(args.csv_path, db=db)
        count = ingester.ingest()
        print(f"Ingested {count} contacts")
    finally:
        db.close()


if __name__ == '__main__':
    main()
