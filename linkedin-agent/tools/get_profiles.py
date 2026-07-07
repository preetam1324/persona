"""Get enriched profile details for LinkedIn leads."""

from __future__ import annotations

from typing import Any

from persona.core.tool import Tool, ToolResult


class GetProfilesTool(Tool):
    name = "get_profiles"
    description = (
        "Get detailed profile information for specific LinkedIn leads. "
        "Accepts a list of profile IDs or a campaign ID to fetch all leads."
    )
    parameters = {
        "type": "object",
        "properties": {
            "profile_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of LinkedIn profile IDs to fetch",
            },
            "campaign_id": {
                "type": "string",
                "description": "Campaign ID — fetch all leads for this campaign",
            },
        },
        "required": [],
    }

    linkedin_provider: Any = None
    db: Any = None

    async def execute(self, **kwargs: Any) -> ToolResult:
        from db.repository import LeadRepository

        if not self.linkedin_provider:
            return ToolResult(output=None, error="LinkedIn provider not configured")

        profile_ids: list[str] = kwargs.get("profile_ids", [])
        campaign_id: str | None = kwargs.get("campaign_id")

        # If campaign_id given, get all lead profile IDs from DB
        if campaign_id and self.db and not profile_ids:
            async with self.db.session() as session:
                lead_repo = LeadRepository(session)
                pairs = await lead_repo.get_campaign_leads(campaign_id)
                profile_ids = [lead.linkedin_profile_id for _, lead in pairs]

        if not profile_ids:
            return ToolResult(output={"count": 0, "profiles": []})

        profiles = []
        for pid in profile_ids:
            try:
                p = await self.linkedin_provider.get_profile(pid)
                profiles.append({
                    "id": p.id,
                    "name": p.name,
                    "title": p.title,
                    "company": p.company,
                    "location": p.location,
                    "headline": p.headline,
                    "summary": p.summary,
                    "profile_url": p.profile_url,
                    "industry": p.industry,
                })

                # Update DB if available
                if self.db:
                    async with self.db.session() as session:
                        lead_repo = LeadRepository(session)
                        await lead_repo.upsert(
                            linkedin_profile_id=p.id,
                            name=p.name,
                            title=p.title,
                            company=p.company,
                            location=p.location,
                            headline=p.headline,
                            profile_url=p.profile_url,
                            raw_data=p.raw_data,
                        )
            except Exception as e:
                profiles.append({"id": pid, "error": str(e)})

        return ToolResult(output={"count": len(profiles), "profiles": profiles})
