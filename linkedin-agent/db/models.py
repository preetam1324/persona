"""SQLAlchemy async models for the LinkedIn agent."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from persona.storage.database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


# ─── Enums ────────────────────────────────────────────────────────────────────

import enum


class CampaignStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    completed = "completed"


class LeadStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    replied = "replied"
    qualified = "qualified"
    rejected = "rejected"


class MessageDirection(str, enum.Enum):
    outbound = "outbound"
    inbound = "inbound"


class MessageType(str, enum.Enum):
    template = "template"
    custom = "custom"


class ConversationStatus(str, enum.Enum):
    active = "active"
    closed = "closed"


# ─── Tables ───────────────────────────────────────────────────────────────────


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    criteria_json: Mapped[dict] = mapped_column(JSON, default=dict)
    interval_weeks: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus), default=CampaignStatus.active
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    campaign_leads: Mapped[list["CampaignLead"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    linkedin_profile_id: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500), default="")
    company: Mapped[str] = mapped_column(String(255), default="")
    location: Mapped[str] = mapped_column(String(255), default="")
    headline: Mapped[str] = mapped_column(Text, default="")
    profile_url: Mapped[str] = mapped_column(String(500), default="")
    raw_data_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    campaign_leads: Mapped[list["CampaignLead"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan"
    )


class CampaignLead(Base):
    __tablename__ = "campaign_leads"
    __table_args__ = (
        UniqueConstraint("campaign_id", "lead_id", name="uq_campaign_lead"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"))
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus), default=LeadStatus.new
    )
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    campaign: Mapped["Campaign"] = relationship(back_populates="campaign_leads")
    lead: Mapped["Lead"] = relationship(back_populates="campaign_leads")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="campaign_lead", cascade="all, delete-orphan"
    )
    conversation: Mapped["ConversationRecord | None"] = relationship(
        back_populates="campaign_lead", uselist=False
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    campaign_lead_id: Mapped[str] = mapped_column(
        ForeignKey("campaign_leads.id", ondelete="CASCADE")
    )
    direction: Mapped[MessageDirection] = mapped_column(Enum(MessageDirection))
    content: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    message_type: Mapped[MessageType] = mapped_column(
        Enum(MessageType), default=MessageType.template
    )

    campaign_lead: Mapped["CampaignLead"] = relationship(back_populates="messages")


class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    body_template: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ConversationRecord(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    campaign_lead_id: Mapped[str] = mapped_column(
        ForeignKey("campaign_leads.id", ondelete="CASCADE"), unique=True
    )
    linkedin_conversation_id: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus), default=ConversationStatus.active
    )
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    campaign_lead: Mapped["CampaignLead"] = relationship(
        back_populates="conversation"
    )
