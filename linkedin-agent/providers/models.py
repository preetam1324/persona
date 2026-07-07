"""Pydantic models for LinkedIn data structures."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SearchCriteria(BaseModel):
    """Criteria for searching LinkedIn profiles."""

    title: str | None = None
    industry: str | None = None
    location: str | None = None
    company: str | None = None
    company_size: str | None = None  # e.g. "51-200", "201-500"
    keywords: list[str] = Field(default_factory=list)
    max_results: int = 25


class LinkedInProfile(BaseModel):
    """A LinkedIn profile result."""

    id: str  # Unique identifier (provider-specific)
    name: str
    title: str = ""
    company: str = ""
    location: str = ""
    headline: str = ""
    summary: str = ""
    profile_url: str = ""
    industry: str = ""
    connection_degree: int | None = None
    raw_data: dict = Field(default_factory=dict)


class MessageResult(BaseModel):
    """Result of sending a message."""

    success: bool
    message_id: str | None = None
    error: str | None = None


class ConversationMessage(BaseModel):
    """A single message in a LinkedIn conversation."""

    sender_id: str
    sender_name: str
    content: str
    timestamp: datetime
    is_outbound: bool = False


class Conversation(BaseModel):
    """A LinkedIn conversation thread."""

    conversation_id: str
    participant_id: str
    participant_name: str
    messages: list[ConversationMessage] = Field(default_factory=list)
    last_message_at: datetime | None = None
