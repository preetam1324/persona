"""Tests for database repository CRUD operations."""

import pytest

from db.models import (
    CampaignStatus,
    ConversationStatus,
    LeadStatus,
    MessageDirection,
    MessageType,
)
from db.repository import CampaignRepository, LeadRepository, MessageRepository


# ─── CampaignRepository ──────────────────────────────────────────────────────


class TestCampaignRepository:
    @pytest.mark.asyncio
    async def test_create_campaign(self, test_db):
        async with test_db.session() as session:
            repo = CampaignRepository(session)
            campaign = await repo.create(
                name="Q3 Outreach",
                criteria={"title": "VP"},
                interval_weeks=2,
            )
            assert campaign.id is not None
            assert campaign.name == "Q3 Outreach"
            assert campaign.status == CampaignStatus.active
            assert campaign.interval_weeks == 2

    @pytest.mark.asyncio
    async def test_get_campaign(self, test_db):
        async with test_db.session() as session:
            repo = CampaignRepository(session)
            created = await repo.create(name="Test", criteria={})
            campaign_id = created.id

        async with test_db.session() as session:
            repo = CampaignRepository(session)
            fetched = await repo.get(campaign_id)
            assert fetched is not None
            assert fetched.name == "Test"

    @pytest.mark.asyncio
    async def test_get_nonexistent_campaign(self, test_db):
        async with test_db.session() as session:
            repo = CampaignRepository(session)
            fetched = await repo.get("nonexistent-id")
            assert fetched is None

    @pytest.mark.asyncio
    async def test_list_active_campaigns(self, test_db):
        async with test_db.session() as session:
            repo = CampaignRepository(session)
            await repo.create(name="Active1", criteria={})
            await repo.create(name="Active2", criteria={})

        async with test_db.session() as session:
            repo = CampaignRepository(session)
            active = await repo.list_active()
            assert len(active) >= 2

    @pytest.mark.asyncio
    async def test_list_all_campaigns(self, test_db):
        async with test_db.session() as session:
            repo = CampaignRepository(session)
            await repo.create(name="C1", criteria={})

        async with test_db.session() as session:
            repo = CampaignRepository(session)
            all_campaigns = await repo.list_all()
            assert len(all_campaigns) >= 1

    @pytest.mark.asyncio
    async def test_update_status(self, test_db):
        async with test_db.session() as session:
            repo = CampaignRepository(session)
            created = await repo.create(name="Test", criteria={})
            campaign_id = created.id

        async with test_db.session() as session:
            repo = CampaignRepository(session)
            await repo.update_status(campaign_id, CampaignStatus.paused)

        async with test_db.session() as session:
            repo = CampaignRepository(session)
            fetched = await repo.get(campaign_id)
            assert fetched.status == CampaignStatus.paused

    @pytest.mark.asyncio
    async def test_delete_campaign(self, test_db):
        async with test_db.session() as session:
            repo = CampaignRepository(session)
            created = await repo.create(name="ToDelete", criteria={})
            campaign_id = created.id

        async with test_db.session() as session:
            repo = CampaignRepository(session)
            await repo.delete(campaign_id)

        async with test_db.session() as session:
            repo = CampaignRepository(session)
            fetched = await repo.get(campaign_id)
            assert fetched is None


# ─── LeadRepository ──────────────────────────────────────────────────────────


class TestLeadRepository:
    @pytest.mark.asyncio
    async def test_upsert_insert(self, test_db):
        async with test_db.session() as session:
            repo = LeadRepository(session)
            lead = await repo.upsert(
                linkedin_profile_id="test-001",
                name="Test User",
                title="Engineer",
                company="TestCo",
            )
            assert lead.id is not None
            assert lead.name == "Test User"

    @pytest.mark.asyncio
    async def test_upsert_update(self, test_db):
        async with test_db.session() as session:
            repo = LeadRepository(session)
            await repo.upsert(
                linkedin_profile_id="test-001",
                name="Test User",
                title="Engineer",
            )

        async with test_db.session() as session:
            repo = LeadRepository(session)
            lead = await repo.upsert(
                linkedin_profile_id="test-001",
                name="Test User Updated",
                title="Senior Engineer",
            )
            assert lead.name == "Test User Updated"
            assert lead.title == "Senior Engineer"

    @pytest.mark.asyncio
    async def test_link_to_campaign(self, test_db):
        async with test_db.session() as session:
            camp_repo = CampaignRepository(session)
            campaign = await camp_repo.create(name="C1", criteria={})
            lead_repo = LeadRepository(session)
            lead = await lead_repo.upsert(
                linkedin_profile_id="test-001", name="User1"
            )
            cl = await lead_repo.link_to_campaign(campaign.id, lead.id)
            assert cl.campaign_id == campaign.id
            assert cl.lead_id == lead.id
            assert cl.status == LeadStatus.new

    @pytest.mark.asyncio
    async def test_link_to_campaign_idempotent(self, test_db):
        async with test_db.session() as session:
            camp_repo = CampaignRepository(session)
            campaign = await camp_repo.create(name="C1", criteria={})
            lead_repo = LeadRepository(session)
            lead = await lead_repo.upsert(
                linkedin_profile_id="test-001", name="User1"
            )
            cl1 = await lead_repo.link_to_campaign(campaign.id, lead.id)
            cl2 = await lead_repo.link_to_campaign(campaign.id, lead.id)
            assert cl1.id == cl2.id  # same record returned

    @pytest.mark.asyncio
    async def test_get_campaign_leads(self, seeded_db):
        db, campaign_id = seeded_db
        async with db.session() as session:
            repo = LeadRepository(session)
            pairs = await repo.get_campaign_leads(campaign_id)
            assert len(pairs) == 2

    @pytest.mark.asyncio
    async def test_get_campaign_leads_filter_status(self, seeded_db):
        db, campaign_id = seeded_db
        async with db.session() as session:
            repo = LeadRepository(session)
            pairs = await repo.get_campaign_leads(
                campaign_id, status=LeadStatus.new
            )
            assert len(pairs) == 2
            pairs_contacted = await repo.get_campaign_leads(
                campaign_id, status=LeadStatus.contacted
            )
            assert len(pairs_contacted) == 0

    @pytest.mark.asyncio
    async def test_update_lead_status(self, seeded_db):
        db, campaign_id = seeded_db
        async with db.session() as session:
            repo = LeadRepository(session)
            pairs = await repo.get_campaign_leads(campaign_id)
            cl_id = pairs[0][0].id
            await repo.update_lead_status(cl_id, LeadStatus.contacted)

        async with db.session() as session:
            repo = LeadRepository(session)
            pairs = await repo.get_campaign_leads(
                campaign_id, status=LeadStatus.contacted
            )
            assert len(pairs) == 1

    @pytest.mark.asyncio
    async def test_get_lead_by_profile_id(self, seeded_db):
        db, _ = seeded_db
        async with db.session() as session:
            repo = LeadRepository(session)
            lead = await repo.get_lead_by_profile_id("mock-001")
            assert lead is not None
            assert lead.name == "Alice Johnson"

            missing = await repo.get_lead_by_profile_id("nonexistent")
            assert missing is None


# ─── MessageRepository ────────────────────────────────────────────────────────


class TestMessageRepository:
    @pytest.mark.asyncio
    async def test_record_outbound_message(self, seeded_db):
        db, campaign_id = seeded_db
        async with db.session() as session:
            lead_repo = LeadRepository(session)
            pairs = await lead_repo.get_campaign_leads(campaign_id)
            cl_id = pairs[0][0].id

            msg_repo = MessageRepository(session)
            msg = await msg_repo.record_message(
                campaign_lead_id=cl_id,
                content="Hello!",
                direction=MessageDirection.outbound,
                message_type=MessageType.template,
            )
            assert msg.id is not None
            assert msg.direction == MessageDirection.outbound

    @pytest.mark.asyncio
    async def test_record_inbound_message(self, seeded_db):
        db, campaign_id = seeded_db
        async with db.session() as session:
            lead_repo = LeadRepository(session)
            pairs = await lead_repo.get_campaign_leads(campaign_id)
            cl_id = pairs[0][0].id

            msg_repo = MessageRepository(session)
            msg = await msg_repo.record_message(
                campaign_lead_id=cl_id,
                content="Thanks for reaching out!",
                direction=MessageDirection.inbound,
            )
            assert msg.direction == MessageDirection.inbound

    @pytest.mark.asyncio
    async def test_create_template(self, test_db):
        async with test_db.session() as session:
            repo = MessageRepository(session)
            tmpl = await repo.get_or_create_template(
                name="outreach_v1",
                body="Hi {name}, I noticed your work at {company}.",
            )
            assert tmpl.id is not None
            assert tmpl.name == "outreach_v1"

    @pytest.mark.asyncio
    async def test_update_template(self, test_db):
        async with test_db.session() as session:
            repo = MessageRepository(session)
            await repo.get_or_create_template(name="t1", body="v1")

        async with test_db.session() as session:
            repo = MessageRepository(session)
            tmpl = await repo.get_or_create_template(name="t1", body="v2")
            assert tmpl.body_template == "v2"

    @pytest.mark.asyncio
    async def test_get_template(self, test_db):
        async with test_db.session() as session:
            repo = MessageRepository(session)
            await repo.get_or_create_template(name="t1", body="body")

        async with test_db.session() as session:
            repo = MessageRepository(session)
            found = await repo.get_template("t1")
            assert found is not None
            assert found.body_template == "body"

            missing = await repo.get_template("nonexistent")
            assert missing is None

    @pytest.mark.asyncio
    async def test_list_templates(self, test_db):
        async with test_db.session() as session:
            repo = MessageRepository(session)
            await repo.get_or_create_template(name="t1", body="b1")
            await repo.get_or_create_template(name="t2", body="b2")

        async with test_db.session() as session:
            repo = MessageRepository(session)
            templates = await repo.list_templates()
            assert len(templates) >= 2

    @pytest.mark.asyncio
    async def test_upsert_conversation_create(self, seeded_db):
        db, campaign_id = seeded_db
        async with db.session() as session:
            lead_repo = LeadRepository(session)
            pairs = await lead_repo.get_campaign_leads(campaign_id)
            cl_id = pairs[0][0].id

            msg_repo = MessageRepository(session)
            conv = await msg_repo.upsert_conversation(
                campaign_lead_id=cl_id,
                linkedin_conversation_id="conv-123",
            )
            assert conv.id is not None
            assert conv.status == ConversationStatus.active

    @pytest.mark.asyncio
    async def test_upsert_conversation_update(self, seeded_db):
        db, campaign_id = seeded_db
        async with db.session() as session:
            lead_repo = LeadRepository(session)
            pairs = await lead_repo.get_campaign_leads(campaign_id)
            cl_id = pairs[0][0].id
            msg_repo = MessageRepository(session)
            await msg_repo.upsert_conversation(
                campaign_lead_id=cl_id,
                linkedin_conversation_id="conv-123",
            )

        async with db.session() as session:
            msg_repo = MessageRepository(session)
            conv = await msg_repo.upsert_conversation(
                campaign_lead_id=cl_id,
                linkedin_conversation_id="conv-456",
            )
            assert conv.linkedin_conversation_id == "conv-456"
