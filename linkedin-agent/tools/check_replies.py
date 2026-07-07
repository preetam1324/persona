"""Check for replies from contacted LinkedIn leads."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from persona.core.tool import Tool, ToolResult


class CheckRepliesTool(Tool):
    name = "check_replies"
    description = (
        "Check for new replies from LinkedIn leads who were previously contacted. "
        "Updates the database with reply status and returns a summary of who replied."
    )
    parameters = {
        "type": "object",
        "properties": {
            "campaign_id": {
                "type": "string",
                "description": "Campaign ID to check replies for. If omitted, checks all active campaigns.",
            },
        },
        "required": [],
    }

    linkedin_provider: Any = None
    db: Any = None

    async def execute(self, **kwargs: Any) -> ToolResult:
        from db.models import LeadStatus, MessageDirection, MessageType
        from db.repository import (
            CampaignRepository,
            LeadRepository,
            MessageRepository,
        )

        campaign_id = kwargs.get("campaign_id")

        if not self.linkedin_provider:
            return ToolResult(output=None, error="LinkedIn provider not configured")
        if not self.db:
            return ToolResult(output=None, error="Database not configured")

        # Get conversations from LinkedIn
        try:
            conversations = await self.linkedin_provider.get_conversations()
        except Exception as e:
            return ToolResult(output=None, error=f"Failed to fetch conversations: {e}")

        # Determine which campaigns to check
        async with self.db.session() as session:
            campaign_repo = CampaignRepository(session)
            if campaign_id:
                campaigns = [await campaign_repo.get(campaign_id)]
                campaigns = [c for c in campaigns if c]
            else:
                campaigns = await campaign_repo.list_active()

        replies: list[dict[str, Any]] = []

        for campaign in campaigns:
            async with self.db.session() as session:
                lead_repo = LeadRepository(session)
                msg_repo = MessageRepository(session)

                # Get contacted leads for this campaign
                contacted = await lead_repo.get_campaign_leads(
                    campaign.id, status=LeadStatus.contacted
                )

                for cl, lead in contacted:
                    # Check if any conversation matches this lead
                    for conv in conversations:
                        if conv.participant_id == lead.linkedin_profile_id:
                            # Found a reply — update status and record messages
                            await lead_repo.update_lead_status(
                                cl.id, LeadStatus.replied
                            )

                            # Record inbound messages
                            for msg in conv.messages:
                                if not msg.is_outbound:
                                    await msg_repo.record_message(
                                        campaign_lead_id=cl.id,
                                        content=msg.content,
                                        direction=MessageDirection.inbound,
                                        message_type=MessageType.custom,
                                    )

                            # Create/update conversation record
                            await msg_repo.upsert_conversation(
                                campaign_lead_id=cl.id,
                                linkedin_conversation_id=conv.conversation_id,
                                last_message_at=conv.last_message_at,
                            )

                            latest_msg = ""
                            if conv.messages:
                                inbound = [m for m in conv.messages if not m.is_outbound]
                                if inbound:
                                    latest_msg = inbound[-1].content

                            replies.append({
                                "campaign_id": campaign.id,
                                "campaign_name": campaign.name,
                                "lead_name": lead.name,
                                "lead_title": lead.title,
                                "lead_company": lead.company,
                                "latest_reply": latest_msg,
                                "conversation_id": conv.conversation_id,
                            })

        return ToolResult(
            output={
                "reply_count": len(replies),
                "replies": replies,
                "message": (
                    f"Found {len(replies)} new replies"
                    if replies
                    else "No new replies found"
                ),
            }
        )
