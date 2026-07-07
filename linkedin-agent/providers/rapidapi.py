"""RapidAPI-based LinkedIn provider (stub — plug in your API of choice)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from providers.base import LinkedInProvider
from providers.models import (
    Conversation,
    LinkedInProfile,
    MessageResult,
    SearchCriteria,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://linkedin-api8.p.rapidapi.com"  # Example — replace with your RapidAPI endpoint


class RapidAPILinkedInProvider(LinkedInProvider):
    """LinkedIn access via a RapidAPI endpoint (e.g. Proxycurl, linkedin-api).

    This is a structural stub. You must:
    1. Subscribe to a LinkedIn data API on RapidAPI.
    2. Update _BASE_URL and the endpoint paths to match the API you chose.
    3. Map the API's response schema to LinkedInProfile/Conversation models.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "linkedin-api8.p.rapidapi.com",
        }

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{_BASE_URL}{path}",
                headers=self._headers,
                params=params or {},
                timeout=30.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def search_people(
        self, criteria: SearchCriteria
    ) -> list[LinkedInProfile]:
        params: dict[str, Any] = {}
        if criteria.keywords:
            params["keywords"] = " ".join(criteria.keywords)
        if criteria.title:
            params["title"] = criteria.title
        if criteria.location:
            params["location"] = criteria.location
        if criteria.industry:
            params["industry"] = criteria.industry
        if criteria.company:
            params["company"] = criteria.company

        try:
            data = await self._get("/search-people", params=params)
        except Exception as e:
            logger.error(f"LinkedIn search failed: {e}")
            return []

        results: list[LinkedInProfile] = []
        for item in data.get("results", data.get("data", []))[:criteria.max_results]:
            results.append(
                LinkedInProfile(
                    id=item.get("id", item.get("profile_id", "")),
                    name=item.get("name", item.get("full_name", "")),
                    title=item.get("title", item.get("job_title", "")),
                    company=item.get("company", item.get("company_name", "")),
                    location=item.get("location", ""),
                    headline=item.get("headline", ""),
                    summary=item.get("summary", ""),
                    profile_url=item.get("profile_url", item.get("linkedin_url", "")),
                    industry=item.get("industry", ""),
                    raw_data=item,
                )
            )
        return results

    async def get_profile(self, profile_id: str) -> LinkedInProfile:
        try:
            data = await self._get(f"/profile/{profile_id}")
        except Exception as e:
            logger.error(f"Profile fetch failed for {profile_id}: {e}")
            return LinkedInProfile(id=profile_id, name="Unknown")

        return LinkedInProfile(
            id=profile_id,
            name=data.get("name", data.get("full_name", "")),
            title=data.get("title", data.get("job_title", "")),
            company=data.get("company", data.get("company_name", "")),
            location=data.get("location", ""),
            headline=data.get("headline", ""),
            summary=data.get("summary", ""),
            profile_url=data.get("profile_url", data.get("linkedin_url", "")),
            industry=data.get("industry", ""),
            raw_data=data,
        )

    async def send_message(
        self, profile_id: str, message: str
    ) -> MessageResult:
        # Most RapidAPI LinkedIn endpoints do NOT support sending messages.
        # This would require OAuth-based access or browser automation.
        logger.warning(
            "RapidAPI provider does not support sending messages. "
            "Implement via official API or browser automation."
        )
        return MessageResult(
            success=False,
            error="Message sending not supported by this provider. "
            "Use official LinkedIn API or browser automation.",
        )

    async def get_conversations(
        self, since: datetime | None = None
    ) -> list[Conversation]:
        logger.warning("RapidAPI provider does not support conversation access.")
        return []

    async def reply_to_conversation(
        self, conversation_id: str, message: str
    ) -> MessageResult:
        logger.warning("RapidAPI provider does not support replying to conversations.")
        return MessageResult(
            success=False,
            error="Reply not supported by this provider.",
        )
