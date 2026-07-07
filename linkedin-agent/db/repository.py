"""Repository classes for LinkedIn agent database operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    Campaign,
    CampaignLead,
    CampaignStatus,
    ConversationRecord,
    ConversationStatus,
    Lead,
    LeadStatus,
    Message,
    MessageDirection,
    MessageTemplate,
    MessageType,
)


class CampaignRepository:
    """CRUD operations for campaigns."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        name: str,
        criteria: dict[str, Any],
        interval_weeks: int = 1,
    ) -> Campaign:
        campaign = Campaign(
            name=name,
            criteria_json=criteria,
            interval_weeks=interval_weeks,
            status=CampaignStatus.active,
        )
        self.session.add(campaign)
        await self.session.flush()
        return campaign

    async def get(self, campaign_id: str) -> Campaign | None:
        return await self.session.get(Campaign, campaign_id)

    async def list_active(self) -> list[Campaign]:
        result = await self.session.execute(
            select(Campaign).where(Campaign.status == CampaignStatus.active)
        )
        return list(result.scalars().all())

    async def list_all(self) -> list[Campaign]:
        result = await self.session.execute(select(Campaign))
        return list(result.scalars().all())

    async def update_status(self, campaign_id: str, status: CampaignStatus) -> None:
        await self.session.execute(
            update(Campaign)
            .where(Campaign.id == campaign_id)
            .values(status=status)
        )

    async def update_next_run(self, campaign_id: str, next_run: datetime) -> None:
        await self.session.execute(
            update(Campaign)
            .where(Campaign.id == campaign_id)
            .values(next_run_at=next_run)
        )

    async def delete(self, campaign_id: str) -> None:
        campaign = await self.get(campaign_id)
        if campaign:
            await self.session.delete(campaign)


class LeadRepository:
    """CRUD operations for leads and campaign-lead associations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self,
        linkedin_profile_id: str,
        name: str,
        title: str = "",
        company: str = "",
        location: str = "",
        headline: str = "",
        profile_url: str = "",
        raw_data: dict | None = None,
    ) -> Lead:
        """Insert or update a lead by linkedin_profile_id."""
        result = await self.session.execute(
            select(Lead).where(Lead.linkedin_profile_id == linkedin_profile_id)
        )
        lead = result.scalar_one_or_none()

        if lead:
            lead.name = name
            lead.title = title
            lead.company = company
            lead.location = location
            lead.headline = headline
            lead.profile_url = profile_url
            if raw_data:
                lead.raw_data_json = raw_data
        else:
            lead = Lead(
                linkedin_profile_id=linkedin_profile_id,
                name=name,
                title=title,
                company=company,
                location=location,
                headline=headline,
                profile_url=profile_url,
                raw_data_json=raw_data or {},
            )
            self.session.add(lead)

        await self.session.flush()
        return lead

    async def link_to_campaign(
        self, campaign_id: str, lead_id: str
    ) -> CampaignLead:
        """Associate a lead with a campaign (idempotent)."""
        result = await self.session.execute(
            select(CampaignLead).where(
                CampaignLead.campaign_id == campaign_id,
                CampaignLead.lead_id == lead_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        cl = CampaignLead(campaign_id=campaign_id, lead_id=lead_id)
        self.session.add(cl)
        await self.session.flush()
        return cl

    async def get_campaign_leads(
        self,
        campaign_id: str,
        status: LeadStatus | None = None,
    ) -> list[tuple[CampaignLead, Lead]]:
        stmt = (
            select(CampaignLead, Lead)
            .join(Lead, CampaignLead.lead_id == Lead.id)
            .where(CampaignLead.campaign_id == campaign_id)
        )
        if status:
            stmt = stmt.where(CampaignLead.status == status)
        result = await self.session.execute(stmt)
        return list(result.all())

    async def update_lead_status(
        self, campaign_lead_id: str, status: LeadStatus
    ) -> None:
        await self.session.execute(
            update(CampaignLead)
            .where(CampaignLead.id == campaign_lead_id)
            .values(status=status)
        )

    async def get_lead_by_profile_id(
        self, linkedin_profile_id: str
    ) -> Lead | None:
        result = await self.session.execute(
            select(Lead).where(Lead.linkedin_profile_id == linkedin_profile_id)
        )
        return result.scalar_one_or_none()


class MessageRepository:
    """CRUD operations for messages, templates, and conversations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record_message(
        self,
        campaign_lead_id: str,
        content: str,
        direction: MessageDirection,
        message_type: MessageType = MessageType.template,
    ) -> Message:
        msg = Message(
            campaign_lead_id=campaign_lead_id,
            direction=direction,
            content=content,
            message_type=message_type,
        )
        self.session.add(msg)
        await self.session.flush()
        return msg

    async def get_or_create_template(
        self, name: str, body: str
    ) -> MessageTemplate:
        result = await self.session.execute(
            select(MessageTemplate).where(MessageTemplate.name == name)
        )
        tmpl = result.scalar_one_or_none()
        if tmpl:
            tmpl.body_template = body
        else:
            tmpl = MessageTemplate(name=name, body_template=body)
            self.session.add(tmpl)
        await self.session.flush()
        return tmpl

    async def get_template(self, name: str) -> MessageTemplate | None:
        result = await self.session.execute(
            select(MessageTemplate).where(MessageTemplate.name == name)
        )
        return result.scalar_one_or_none()

    async def list_templates(self) -> list[MessageTemplate]:
        result = await self.session.execute(select(MessageTemplate))
        return list(result.scalars().all())

    async def upsert_conversation(
        self,
        campaign_lead_id: str,
        linkedin_conversation_id: str,
        last_message_at: datetime | None = None,
    ) -> ConversationRecord:
        result = await self.session.execute(
            select(ConversationRecord).where(
                ConversationRecord.campaign_lead_id == campaign_lead_id
            )
        )
        conv = result.scalar_one_or_none()
        if conv:
            conv.linkedin_conversation_id = linkedin_conversation_id
            if last_message_at:
                conv.last_message_at = last_message_at
        else:
            conv = ConversationRecord(
                campaign_lead_id=campaign_lead_id,
                linkedin_conversation_id=linkedin_conversation_id,
                status=ConversationStatus.active,
                last_message_at=last_message_at,
            )
            self.session.add(conv)
        await self.session.flush()
        return conv
