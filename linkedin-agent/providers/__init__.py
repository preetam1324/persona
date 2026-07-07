"""LinkedIn provider package — pluggable LinkedIn API access."""

from providers.base import LinkedInProvider
from providers.models import (
    Conversation,
    ConversationMessage,
    LinkedInProfile,
    MessageResult,
    SearchCriteria,
)

__all__ = [
    "LinkedInProvider",
    "SearchCriteria",
    "LinkedInProfile",
    "MessageResult",
    "Conversation",
    "ConversationMessage",
]


def create_linkedin_provider(
    provider_type: str, secrets: dict[str, str]
) -> LinkedInProvider:
    """Factory — create a LinkedIn provider by type name."""
    if provider_type == "mock":
        from providers.mock import MockLinkedInProvider

        return MockLinkedInProvider()
    elif provider_type == "rapidapi":
        from providers.rapidapi import RapidAPILinkedInProvider

        return RapidAPILinkedInProvider(api_key=secrets.get("LINKEDIN_API_KEY", ""))
    else:
        raise ValueError(f"Unknown LinkedIn provider type: {provider_type}")
