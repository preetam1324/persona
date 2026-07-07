"""Search LinkedIn for leads matching given criteria."""

from __future__ import annotations

from typing import Any

from persona.core.tool import Tool, ToolResult


class SearchLeadsTool(Tool):
    name = "search_leads"
    description = (
        "Search LinkedIn for potential leads based on criteria such as "
        "job title, industry, location, company, and keywords. "
        "Returns a list of matching profiles and stores them in the database."
    )
    parameters = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Job title to search for (e.g. 'VP of Engineering')",
            },
            "industry": {
                "type": "string",
                "description": "Industry filter (e.g. 'Technology', 'Finance')",
            },
            "location": {
                "type": "string",
                "description": "Location filter (e.g. 'San Francisco, CA')",
            },
            "company": {
                "type": "string",
                "description": "Company name filter",
            },
            "company_size": {
                "type": "string",
                "description": "Company size range (e.g. '51-200', '201-500')",
            },
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Additional keywords to filter by",
            },
            "campaign_id": {
                "type": "string",
                "description": "Campaign ID to associate the leads with",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (default 25)",
                "default": 25,
            },
        },
        "required": [],
    }

    # Injected by the agent at startup
    linkedin_provider: Any = None
    db: Any = None

    async def execute(self, **kwargs: Any) -> ToolResult:
        from db.repository import LeadRepository
        from providers.models import SearchCriteria

        if not self.linkedin_provider:
            return ToolResult(output=None, error="LinkedIn provider not configured")

        criteria = SearchCriteria(
            title=kwargs.get("title"),
            industry=kwargs.get("industry"),
            location=kwargs.get("location"),
            company=kwargs.get("company"),
            company_size=kwargs.get("company_size"),
            keywords=kwargs.get("keywords", []),
            max_results=kwargs.get("max_results", 25),
        )

        try:
            profiles = await self.linkedin_provider.search_people(criteria)
        except Exception as e:
            return ToolResult(output=None, error=f"LinkedIn search failed: {e}")

        campaign_id = kwargs.get("campaign_id")

        # Store leads in DB if database is available
        if self.db and campaign_id:
            async with self.db.session() as session:
                lead_repo = LeadRepository(session)
                for p in profiles:
                    lead = await lead_repo.upsert(
                        linkedin_profile_id=p.id,
                        name=p.name,
                        title=p.title,
                        company=p.company,
                        location=p.location,
                        headline=p.headline,
                        profile_url=p.profile_url,
                        raw_data=p.raw_data,
                    )
                    await lead_repo.link_to_campaign(campaign_id, lead.id)

        results = [
            {
                "id": p.id,
                "name": p.name,
                "title": p.title,
                "company": p.company,
                "location": p.location,
                "headline": p.headline,
                "profile_url": p.profile_url,
            }
            for p in profiles
        ]

        return ToolResult(
            output={
                "count": len(results),
                "profiles": results,
                "campaign_id": campaign_id,
            }
        )
