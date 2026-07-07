"""Shared fixtures for LinkedIn agent tests."""

import sys
from pathlib import Path

import pytest
import pytest_asyncio

# Put agent root on sys.path so imports work like at runtime
agent_root = str(Path(__file__).resolve().parent.parent)
if agent_root not in sys.path:
    sys.path.insert(0, agent_root)

from persona.storage.database import Base, Database  # noqa: E402
from providers.mock import MockLinkedInProvider  # noqa: E402

# Use SQLite for tests — no PostgreSQL required
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def mock_provider():
    """Return a fresh MockLinkedInProvider."""
    return MockLinkedInProvider()


@pytest_asyncio.fixture
async def test_db():
    """Create an in-memory SQLite database with all tables."""
    # Import models to register them with Base
    import db.models  # noqa: F401

    database = Database(url=TEST_DB_URL)
    await database.init(db.models.Base)
    yield database
    await database.close()


@pytest_asyncio.fixture
async def seeded_db(test_db):
    """DB pre-populated with a campaign and leads for tool tests."""
    from db.models import CampaignStatus
    from db.repository import CampaignRepository, LeadRepository

    async with test_db.session() as session:
        camp_repo = CampaignRepository(session)
        campaign = await camp_repo.create(
            name="Test Campaign",
            criteria={"title": "VP", "industry": "Technology"},
            interval_weeks=2,
        )
        campaign_id = campaign.id

        lead_repo = LeadRepository(session)
        lead1 = await lead_repo.upsert(
            linkedin_profile_id="mock-001",
            name="Alice Johnson",
            title="VP of Engineering",
            company="TechCorp",
            location="San Francisco, CA",
            headline="Building the future",
            profile_url="https://linkedin.com/in/alicejohnson",
        )
        lead2 = await lead_repo.upsert(
            linkedin_profile_id="mock-002",
            name="Bob Smith",
            title="CTO",
            company="DataWorks",
            location="New York, NY",
            headline="Data-driven leader",
            profile_url="https://linkedin.com/in/bobsmith",
        )
        await lead_repo.link_to_campaign(campaign_id, lead1.id)
        await lead_repo.link_to_campaign(campaign_id, lead2.id)

    return test_db, campaign_id
