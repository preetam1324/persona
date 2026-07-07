"""Campaign lifecycle management tool."""

from __future__ import annotations

from typing import Any

from persona.core.tool import Tool, ToolResult


class CampaignManagerTool(Tool):
    name = "campaign_manager"
    description = (
        "Manage LinkedIn outreach campaigns. Create new campaigns with search criteria "
        "and scheduling, pause/resume existing campaigns, or list all campaigns."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Action to perform",
                "enum": ["create", "pause", "resume", "list", "delete", "status"],
            },
            "campaign_id": {
                "type": "string",
                "description": "Campaign ID (required for pause/resume/delete/status)",
            },
            "name": {
                "type": "string",
                "description": "Campaign name (for create action)",
            },
            "criteria": {
                "type": "object",
                "description": "Search criteria (for create action). Keys: title, industry, location, company, keywords.",
            },
            "interval_weeks": {
                "type": "integer",
                "description": "How often to run the campaign, in weeks (for create action). Default 2.",
                "default": 2,
            },
        },
        "required": ["action"],
    }

    db: Any = None
    scheduler: Any = None  # AgentScheduler instance, injected at startup

    async def execute(self, **kwargs: Any) -> ToolResult:
        from db.models import CampaignStatus
        from db.repository import CampaignRepository, LeadRepository

        action = kwargs["action"]

        if not self.db:
            return ToolResult(output=None, error="Database not configured")

        if action == "create":
            name = kwargs.get("name", "Untitled Campaign")
            criteria = kwargs.get("criteria", {})
            interval_weeks = kwargs.get("interval_weeks", 2)

            async with self.db.session() as session:
                repo = CampaignRepository(session)
                campaign = await repo.create(
                    name=name,
                    criteria=criteria,
                    interval_weeks=interval_weeks,
                )
                campaign_id = campaign.id

            return ToolResult(
                output={
                    "campaign_id": campaign_id,
                    "name": name,
                    "interval_weeks": interval_weeks,
                    "status": "active",
                    "message": f"Campaign '{name}' created (ID: {campaign_id}). "
                    f"Scheduled to run every {interval_weeks} week(s).",
                }
            )

        elif action == "list":
            async with self.db.session() as session:
                repo = CampaignRepository(session)
                campaigns = await repo.list_all()
                lead_repo = LeadRepository(session)

                result = []
                for c in campaigns:
                    leads = await lead_repo.get_campaign_leads(c.id)
                    result.append({
                        "campaign_id": c.id,
                        "name": c.name,
                        "status": c.status.value,
                        "interval_weeks": c.interval_weeks,
                        "lead_count": len(leads),
                        "created_at": c.created_at.isoformat(),
                    })

            return ToolResult(output={"campaigns": result, "count": len(result)})

        elif action == "status":
            campaign_id = kwargs.get("campaign_id")
            if not campaign_id:
                return ToolResult(output=None, error="campaign_id is required for status")

            async with self.db.session() as session:
                repo = CampaignRepository(session)
                campaign = await repo.get(campaign_id)
                if not campaign:
                    return ToolResult(output=None, error=f"Campaign {campaign_id} not found")

                lead_repo = LeadRepository(session)
                all_leads = await lead_repo.get_campaign_leads(campaign_id)

                from db.models import LeadStatus as LS
                status_counts = {}
                for cl, _ in all_leads:
                    s = cl.status.value
                    status_counts[s] = status_counts.get(s, 0) + 1

            return ToolResult(
                output={
                    "campaign_id": campaign.id,
                    "name": campaign.name,
                    "status": campaign.status.value,
                    "interval_weeks": campaign.interval_weeks,
                    "total_leads": len(all_leads),
                    "lead_status_breakdown": status_counts,
                    "created_at": campaign.created_at.isoformat(),
                    "next_run_at": campaign.next_run_at.isoformat() if campaign.next_run_at else None,
                }
            )

        elif action == "pause":
            campaign_id = kwargs.get("campaign_id")
            if not campaign_id:
                return ToolResult(output=None, error="campaign_id is required for pause")

            async with self.db.session() as session:
                repo = CampaignRepository(session)
                await repo.update_status(campaign_id, CampaignStatus.paused)

            if self.scheduler:
                self.scheduler.cancel(f"campaign_{campaign_id}")

            return ToolResult(output={"campaign_id": campaign_id, "status": "paused"})

        elif action == "resume":
            campaign_id = kwargs.get("campaign_id")
            if not campaign_id:
                return ToolResult(output=None, error="campaign_id is required for resume")

            async with self.db.session() as session:
                repo = CampaignRepository(session)
                await repo.update_status(campaign_id, CampaignStatus.active)

            return ToolResult(
                output={
                    "campaign_id": campaign_id,
                    "status": "active",
                    "message": "Campaign resumed",
                }
            )

        elif action == "delete":
            campaign_id = kwargs.get("campaign_id")
            if not campaign_id:
                return ToolResult(output=None, error="campaign_id is required for delete")

            if self.scheduler:
                self.scheduler.cancel(f"campaign_{campaign_id}")

            async with self.db.session() as session:
                repo = CampaignRepository(session)
                await repo.delete(campaign_id)

            return ToolResult(
                output={"campaign_id": campaign_id, "message": "Campaign deleted"}
            )

        else:
            return ToolResult(output=None, error=f"Unknown action: {action}")
