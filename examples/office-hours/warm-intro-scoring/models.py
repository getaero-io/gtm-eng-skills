"""Data models for warm intro system."""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class Contact:
    """A LinkedIn connection."""
    id: str
    first_name: str
    last_name: str
    linkedin_url: str
    email: Optional[str] = None
    current_company: Optional[str] = None
    current_position: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    connected_on: Optional[date] = None
    enriched_at: Optional[datetime] = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


@dataclass
class Experience:
    """A work experience entry."""
    id: str
    contact_id: str
    company_name: str
    company_linkedin_url: Optional[str] = None
    title: str = ""
    description: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False


@dataclass
class Education:
    """An education entry."""
    id: str
    contact_id: str
    school_name: str
    school_linkedin_url: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None


@dataclass
class Company:
    """Normalized company for deduplication."""
    id: str
    name: str
    linkedin_url: Optional[str] = None
    domain: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None


@dataclass
class Affiliation:
    """A professional affiliation or community membership.

    Types:
    - investor: VC firm that invested in their company
    - board_member: board they sit on
    - advisor: consulting/advisory relationship
    - agency: marketing/sales agency they work with
    - consultant: individual consultant relationship
    - community: professional community (Pavilion, RevOps Co-op, etc.)
    - slack: Slack community membership
    - charity: nonprofit board or volunteer work
    - association: professional association (AMA, IEEE, etc.)
    """
    id: str
    contact_id: str
    affiliation_type: str
    entity_name: str  # VC firm, community name, charity name, etc.
    entity_linkedin_url: Optional[str] = None
    role: Optional[str] = None  # Partner, Member, Board Member, etc.
    target_company: Optional[str] = None  # Company they invested in / advise (for investor type)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = True


@dataclass
class PublicAppearance:
    """A public appearance (podcast, webinar, conference talk, guest post)."""
    id: str
    contact_id: str
    appearance_type: str  # podcast, webinar, conference, guest_post, interview
    title: str
    platform: str  # podcast name, conference name, publication name
    url: Optional[str] = None
    date: Optional[date] = None
    description: Optional[str] = None


@dataclass
class WarmIntroMatch:
    """A potential warm intro path."""
    contact: Contact
    score: float
    reasons: list[str] = field(default_factory=list)
    shared_companies: list[str] = field(default_factory=list)
    shared_schools: list[str] = field(default_factory=list)
    shared_appearances: list[str] = field(default_factory=list)
    shared_affiliations: list[str] = field(default_factory=list)
    role_similarity: float = 0.0
    recency_boost: float = 0.0
