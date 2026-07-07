"""Mock LinkedIn provider for development and testing."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from providers.base import LinkedInProvider
from providers.models import (
    Conversation,
    ConversationMessage,
    LinkedInProfile,
    MessageResult,
    SearchCriteria,
)

_FAKE_PROFILES = [
    LinkedInProfile(
        id="mock-001", name="Alice Johnson", title="VP of Engineering",
        company="TechCorp", location="San Francisco, CA",
        headline="Building the future of cloud infrastructure",
        profile_url="https://linkedin.com/in/alicejohnson", industry="Technology",
    ),
    LinkedInProfile(
        id="mock-002", name="Bob Smith", title="CTO",
        company="DataWorks", location="New York, NY",
        headline="Data-driven leader | Ex-Google",
        profile_url="https://linkedin.com/in/bobsmith", industry="Technology",
    ),
    LinkedInProfile(
        id="mock-003", name="Carol Williams", title="Head of Product",
        company="AI Startup Inc.", location="Austin, TX",
        headline="Product leader passionate about AI",
        profile_url="https://linkedin.com/in/carolwilliams", industry="Technology",
    ),
    LinkedInProfile(
        id="mock-004", name="David Lee", title="Director of Sales",
        company="SalesForce Pro", location="Chicago, IL",
        headline="Helping companies scale their revenue",
        profile_url="https://linkedin.com/in/davidlee", industry="Sales",
    ),
    LinkedInProfile(
        id="mock-005", name="Eva Martinez", title="Senior Engineering Manager",
        company="CloudScale", location="Seattle, WA",
        headline="Engineering leader | Distributed systems",
        profile_url="https://linkedin.com/in/evamartinez", industry="Technology",
    ),
]

class MockLinkedInProvider(LinkedInProvider):
    """Returns fake data for development and testing."""

    def __init__(self) -> None:
        self._sent_messages: dict[str, list[str]] = {}

    async def search_people(
        self, criteria: SearchCriteria
    ) -> list[LinkedInProfile]:
        results = list(_FAKE_PROFILES)
        if criteria.title:
            kw = criteria.title.lower()
            results = [p for p in results if kw in p.title.lower()]
        if criteria.industry:
            kw = criteria.industry.lower()
            results = [p for p in results if kw in p.industry.lower()]
        if criteria.location:
            kw = criteria.location.lower()
            results = [p for p in results if kw in p.location.lower()]
        if criteria.company:
            kw = criteria.company.lower()
            results = [p for p in results if kw in p.company.lower()]
        if criteria.keywords:
            def matches(p: LinkedInProfile) -> bool:
                text = f"{p.title} {p.headline} {p.company}".lower()
                return any(k.lower() in text for k in criteria.keywords)
            results = [p for p in results if matches(p)]
        return results[: criteria.max_results]

    async def get_profile(self, profile_id: str) -> LinkedInProfile:
        for p in _FAKE_PROFILES:
            if p.id == profile_id:
                return p
        return LinkedInProfile(
            id=profile_id, name="Unknown User", profile_url=""
        )

    async def send_message(
        self, profile_id: str, message: str
    ) -> MessageResult:
        self._sent_messages.setdefault(profile_id, []).append(message)
        return MessageResult(
            success=True, message_id=f"msg-{uuid.uuid4().hex[:8]}"
        )

    async def get_conversations(
        self, since: datetime | None = None
    ) -> list[Conversation]:
        # Simulate one reply from Alice
        now = datetime.utcnow()
        if "mock-001" in self._sent_messages:
            return [
                Conversation(
                    conversation_id="conv-001",
                    participant_id="mock-001",
                    participant_name="Alice Johnson",
                    messages=[
                        ConversationMessage(
                            sender_id="mock-001",
                            sender_name="Alice Johnson",
                            content="Thanks for reaching out! I'd love to learn more.",
                            timestamp=now - timedelta(hours=2),
                            is_outbound=False,
                        ),
                    ],
                    last_message_at=now - timedelta(hours=2),
                )
            ]
        return []

    async def reply_to_conversation(
        self, conversation_id: str, message: str
    ) -> MessageResult:
        return MessageResult(
            success=True, message_id=f"reply-{uuid.uuid4().hex[:8]}"
        )
