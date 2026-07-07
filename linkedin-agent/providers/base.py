"""Abstract base class for LinkedIn API providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from providers.models import (
    Conversation,
    LinkedInProfile,
    MessageResult,
    SearchCriteria,
)


class LinkedInProvider(ABC):
    """Abstract interface for LinkedIn operations.

    Concrete implementations can use RapidAPI, Playwright,
    the official LinkedIn API, or any other strategy — the
    agent tools only depend on this interface.
    """

    @abstractmethod
    async def search_people(
        self, criteria: SearchCriteria
    ) -> list[LinkedInProfile]:
        """Search LinkedIn for people matching the given criteria."""
        ...

    @abstractmethod
    async def get_profile(self, profile_id: str) -> LinkedInProfile:
        """Get detailed profile information for a single person."""
        ...

    @abstractmethod
    async def send_message(
        self, profile_id: str, message: str
    ) -> MessageResult:
        """Send a direct message to a LinkedIn profile."""
        ...

    @abstractmethod
    async def get_conversations(
        self, since: datetime | None = None
    ) -> list[Conversation]:
        """Get conversations, optionally filtered to those updated since a timestamp."""
        ...

    @abstractmethod
    async def reply_to_conversation(
        self, conversation_id: str, message: str
    ) -> MessageResult:
        """Reply to an existing LinkedIn conversation."""
        ...
