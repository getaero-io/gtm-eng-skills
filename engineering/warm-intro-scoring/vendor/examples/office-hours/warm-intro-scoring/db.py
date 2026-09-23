"""Database schema and connection helpers for warm intro system."""
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import Contact, Experience, Education, Company, PublicAppearance, Affiliation


class WarmIntroDB:
    """SQLite database for warm intro contacts and career history."""

    DEFAULT_PATH = Path(__file__).parent.parent.parent / "data" / "warm_intros.db"

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(self.DEFAULT_PATH)
        self.conn: Optional[sqlite3.Connection] = None

    def init(self) -> None:
        """Initialize database with schema."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                linkedin_url TEXT UNIQUE NOT NULL,
                email TEXT,
                current_company TEXT,
                current_position TEXT,
                headline TEXT,
                location TEXT,
                connected_on TEXT,
                enriched_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS experiences (
                id TEXT PRIMARY KEY,
                contact_id TEXT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
                company_name TEXT NOT NULL,
                company_linkedin_url TEXT,
                title TEXT,
                description TEXT,
                location TEXT,
                start_date TEXT,
                end_date TEXT,
                is_current INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS educations (
                id TEXT PRIMARY KEY,
                contact_id TEXT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
                school_name TEXT NOT NULL,
                school_linkedin_url TEXT,
                degree TEXT,
                field_of_study TEXT,
                start_year INTEGER,
                end_year INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                linkedin_url TEXT UNIQUE,
                domain TEXT,
                industry TEXT,
                employee_count INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS appearances (
                id TEXT PRIMARY KEY,
                contact_id TEXT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
                appearance_type TEXT NOT NULL,
                title TEXT NOT NULL,
                platform TEXT NOT NULL,
                url TEXT,
                date TEXT,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS affiliations (
                id TEXT PRIMARY KEY,
                contact_id TEXT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
                affiliation_type TEXT NOT NULL,
                entity_name TEXT NOT NULL,
                entity_linkedin_url TEXT,
                role TEXT,
                target_company TEXT,
                start_date TEXT,
                end_date TEXT,
                is_current INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS contact_overlaps (
                id TEXT PRIMARY KEY,
                contact_id_a TEXT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
                contact_id_b TEXT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
                overlap_type TEXT NOT NULL,
                entity_name TEXT NOT NULL,
                entity_name_normalized TEXT NOT NULL,
                overlap_months INTEGER NOT NULL,
                overlap_start TEXT,
                overlap_end TEXT,
                affiliation_subtype TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(contact_id_a, contact_id_b, overlap_type, entity_name_normalized)
            )
        """)

        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_experiences_contact ON experiences(contact_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_experiences_company ON experiences(company_name)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_educations_contact ON educations(contact_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_educations_school ON educations(school_name)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_appearances_contact ON appearances(contact_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_appearances_platform ON appearances(platform)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_affiliations_contact ON affiliations(contact_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_affiliations_entity ON affiliations(entity_name)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_affiliations_type ON affiliations(affiliation_type)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_overlaps_contact_a ON contact_overlaps(contact_id_a)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_overlaps_contact_b ON contact_overlaps(contact_id_b)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_overlaps_entity ON contact_overlaps(entity_name_normalized)")

        self.conn.commit()

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def insert_contact(self, contact: Contact) -> str:
        """Insert or update a contact. Returns contact ID (existing ID on conflict)."""
        assert self.conn is not None

        now = datetime.now(timezone.utc).isoformat()
        contact_id = contact.id or str(uuid.uuid4())

        self.conn.execute("""
            INSERT INTO contacts (id, first_name, last_name, linkedin_url, email,
                                  current_company, current_position, headline, location,
                                  connected_on, enriched_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(linkedin_url) DO UPDATE SET
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                email = COALESCE(excluded.email, contacts.email),
                current_company = COALESCE(excluded.current_company, contacts.current_company),
                current_position = COALESCE(excluded.current_position, contacts.current_position),
                headline = COALESCE(excluded.headline, contacts.headline),
                location = COALESCE(excluded.location, contacts.location),
                enriched_at = COALESCE(excluded.enriched_at, contacts.enriched_at),
                updated_at = excluded.updated_at
        """, (
            contact_id, contact.first_name, contact.last_name, contact.linkedin_url,
            contact.email, contact.current_company, contact.current_position,
            contact.headline, contact.location,
            contact.connected_on.isoformat() if contact.connected_on else None,
            contact.enriched_at.isoformat() if contact.enriched_at else None,
            now
        ))
        self.conn.commit()

        row = self.conn.execute(
            "SELECT id FROM contacts WHERE linkedin_url = ?", (contact.linkedin_url,)
        ).fetchone()
        return row[0]

    def insert_experience(self, exp: Experience) -> str:
        """Insert an experience entry."""
        assert self.conn is not None

        exp_id = exp.id or str(uuid.uuid4())
        self.conn.execute("""
            INSERT INTO experiences (id, contact_id, company_name, company_linkedin_url,
                                     title, description, location, start_date, end_date, is_current)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            exp_id, exp.contact_id, exp.company_name, exp.company_linkedin_url,
            exp.title, exp.description, exp.location,
            exp.start_date.isoformat() if exp.start_date else None,
            exp.end_date.isoformat() if exp.end_date else None,
            1 if exp.is_current else 0
        ))
        self.conn.commit()
        return exp_id

    def insert_education(self, edu: Education) -> str:
        """Insert an education entry."""
        assert self.conn is not None

        edu_id = edu.id or str(uuid.uuid4())
        self.conn.execute("""
            INSERT INTO educations (id, contact_id, school_name, school_linkedin_url,
                                    degree, field_of_study, start_year, end_year)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            edu_id, edu.contact_id, edu.school_name, edu.school_linkedin_url,
            edu.degree, edu.field_of_study, edu.start_year, edu.end_year
        ))
        self.conn.commit()
        return edu_id

    def get_contact_count(self) -> int:
        """Return total number of contacts."""
        assert self.conn is not None
        return self.conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]

    def get_enriched_count(self) -> int:
        """Return number of enriched contacts."""
        assert self.conn is not None
        return self.conn.execute(
            "SELECT COUNT(*) FROM contacts WHERE enriched_at IS NOT NULL"
        ).fetchone()[0]

    def get_unenriched_contacts(self, limit: int = 100) -> list[Contact]:
        """Get contacts that haven't been enriched yet."""
        assert self.conn is not None
        rows = self.conn.execute("""
            SELECT * FROM contacts
            WHERE enriched_at IS NULL
            ORDER BY connected_on DESC
            LIMIT ?
        """, (limit,)).fetchall()

        return [self._row_to_contact(row) for row in rows]

    def _row_to_contact(self, row: sqlite3.Row) -> Contact:
        """Convert a database row to Contact dataclass."""
        from datetime import date

        connected_on = None
        if row['connected_on']:
            connected_on = date.fromisoformat(row['connected_on'])

        enriched_at = None
        if row['enriched_at']:
            enriched_at = datetime.fromisoformat(row['enriched_at'])

        return Contact(
            id=row['id'],
            first_name=row['first_name'],
            last_name=row['last_name'],
            linkedin_url=row['linkedin_url'],
            email=row['email'],
            current_company=row['current_company'],
            current_position=row['current_position'],
            headline=row['headline'],
            location=row['location'],
            connected_on=connected_on,
            enriched_at=enriched_at
        )

    def insert_appearance(self, appearance: PublicAppearance) -> str:
        """Insert an appearance entry. Returns appearance ID."""
        assert self.conn is not None
        from datetime import date

        app_id = appearance.id or str(uuid.uuid4())
        self.conn.execute("""
            INSERT INTO appearances (id, contact_id, appearance_type, title, platform,
                                     url, date, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            app_id, appearance.contact_id, appearance.appearance_type,
            appearance.title, appearance.platform, appearance.url,
            appearance.date.isoformat() if appearance.date else None,
            appearance.description
        ))
        self.conn.commit()
        return app_id

    def get_appearances_by_contact(self, contact_id: str) -> list[PublicAppearance]:
        """Get all appearances for a contact."""
        assert self.conn is not None
        from datetime import date

        rows = self.conn.execute("""
            SELECT * FROM appearances WHERE contact_id = ?
        """, (contact_id,)).fetchall()

        appearances = []
        for row in rows:
            app_date = None
            if row['date']:
                app_date = date.fromisoformat(row['date'])

            appearances.append(PublicAppearance(
                id=row['id'],
                contact_id=row['contact_id'],
                appearance_type=row['appearance_type'],
                title=row['title'],
                platform=row['platform'],
                url=row['url'],
                date=app_date,
                description=row['description']
            ))
        return appearances

    def get_all_appearances(self) -> list[PublicAppearance]:
        """Get all appearances across all contacts."""
        assert self.conn is not None
        from datetime import date

        rows = self.conn.execute("SELECT * FROM appearances").fetchall()

        appearances = []
        for row in rows:
            app_date = None
            if row['date']:
                app_date = date.fromisoformat(row['date'])

            appearances.append(PublicAppearance(
                id=row['id'],
                contact_id=row['contact_id'],
                appearance_type=row['appearance_type'],
                title=row['title'],
                platform=row['platform'],
                url=row['url'],
                date=app_date,
                description=row['description']
            ))
        return appearances

    def insert_affiliation(self, affiliation: Affiliation) -> str:
        """Insert an affiliation entry. Returns affiliation ID."""
        assert self.conn is not None
        from datetime import date

        aff_id = affiliation.id or str(uuid.uuid4())
        self.conn.execute("""
            INSERT INTO affiliations (id, contact_id, affiliation_type, entity_name,
                                      entity_linkedin_url, role, target_company,
                                      start_date, end_date, is_current)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            aff_id, affiliation.contact_id, affiliation.affiliation_type,
            affiliation.entity_name, affiliation.entity_linkedin_url,
            affiliation.role, affiliation.target_company,
            affiliation.start_date.isoformat() if affiliation.start_date else None,
            affiliation.end_date.isoformat() if affiliation.end_date else None,
            1 if affiliation.is_current else 0
        ))
        self.conn.commit()
        return aff_id

    def get_affiliations_by_contact(self, contact_id: str) -> list[Affiliation]:
        """Get all affiliations for a contact."""
        assert self.conn is not None
        from datetime import date

        rows = self.conn.execute("""
            SELECT * FROM affiliations WHERE contact_id = ?
        """, (contact_id,)).fetchall()

        affiliations = []
        for row in rows:
            start_date = None
            if row['start_date']:
                start_date = date.fromisoformat(row['start_date'])
            end_date = None
            if row['end_date']:
                end_date = date.fromisoformat(row['end_date'])

            affiliations.append(Affiliation(
                id=row['id'],
                contact_id=row['contact_id'],
                affiliation_type=row['affiliation_type'],
                entity_name=row['entity_name'],
                entity_linkedin_url=row['entity_linkedin_url'],
                role=row['role'],
                target_company=row['target_company'],
                start_date=start_date,
                end_date=end_date,
                is_current=bool(row['is_current'])
            ))
        return affiliations

    def get_contacts_by_affiliation(self, entity_name: str) -> list[Contact]:
        """Get all contacts affiliated with an entity (VC firm, agency, etc.)."""
        assert self.conn is not None

        rows = self.conn.execute("""
            SELECT DISTINCT c.* FROM contacts c
            JOIN affiliations a ON c.id = a.contact_id
            WHERE LOWER(a.entity_name) LIKE LOWER(?)
        """, (f"%{entity_name}%",)).fetchall()

        return [self._row_to_contact(row) for row in rows]
