"""Send templated or personalized messages to LinkedIn leads."""

from __future__ import annotations

from typing import Any

from persona.core.tool import Tool, ToolResult


class SendMessageTool(Tool):
    name = "send_message"
    description = (
        "Send outreach messages to LinkedIn leads. Supports templated messages "
        "(with {name}, {company}, {title} placeholders) or fully personalized "
        "messages where the AI customizes the message for each lead's profile."
    )
    parameters = {
        "type": "object",
        "properties": {
            "campaign_id": {
                "type": "string",
                "description": "Campaign ID containing the leads",
            },
            "lead_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific LinkedIn profile IDs to message. If empty, messages all 'new' leads.",
            },
            "message_template": {
                "type": "string",
                "description": (
                    "Message template with placeholders like {name}, {company}, {title}. "
                    "Example: 'Hi {name}, I noticed you work at {company}...'"
                ),
            },
            "personalize": {
                "type": "boolean",
                "description": "If true, uses AI to customize the message for each lead's profile. Default false.",
                "default": False,
            },
        },
        "required": ["campaign_id", "message_template"],
    }

    linkedin_provider: Any = None
    db: Any = None
    llm_provider: Any = None  # Injected — the agent's current LLM for personalization

    async def execute(self, **kwargs: Any) -> ToolResult:
        from db.models import LeadStatus, MessageDirection, MessageType
        from db.repository import LeadRepository, MessageRepository
        from persona.core.response import Message as LLMMessage

        campaign_id = kwargs["campaign_id"]
        message_template = kwargs["message_template"]
        target_ids: list[str] = kwargs.get("lead_ids", [])
        personalize: bool = kwargs.get("personalize", False)

        if not self.linkedin_provider:
            return ToolResult(output=None, error="LinkedIn provider not configured")
        if not self.db:
            return ToolResult(output=None, error="Database not configured")

        # Get leads to message
        async with self.db.session() as session:
            lead_repo = LeadRepository(session)
            if target_ids:
                all_pairs = await lead_repo.get_campaign_leads(campaign_id)
                pairs = [
                    (cl, lead) for cl, lead in all_pairs
                    if lead.linkedin_profile_id in target_ids
                ]
            else:
                # Default: message all 'new' leads
                pairs = await lead_repo.get_campaign_leads(
                    campaign_id, status=LeadStatus.new
                )

        if not pairs:
            return ToolResult(output={"sent": 0, "failed": 0, "message": "No leads to message"})

        sent = 0
        failed = 0
        details: list[dict[str, Any]] = []

        for cl, lead in pairs:
            # Build the message
            msg = message_template.format(
                name=lead.name,
                company=lead.company,
                title=lead.title,
                location=lead.location,
                headline=lead.headline,
            )

            # Personalize using LLM if requested
            if personalize and self.llm_provider:
                try:
                    personalize_prompt = [
                        LLMMessage(
                            role="system",
                            content=(
                                "You are a professional message personalizer. "
                                "Rewrite the given outreach message to be more personal and relevant "
                                "based on the recipient's LinkedIn profile. Keep it concise, professional, "
                                "and under 300 characters. Maintain the core intent of the original message."
                            ),
                        ),
                        LLMMessage(
                            role="user",
                            content=(
                                f"Original message:\n{msg}\n\n"
                                f"Recipient profile:\n"
                                f"Name: {lead.name}\n"
                                f"Title: {lead.title}\n"
                                f"Company: {lead.company}\n"
                                f"Headline: {lead.headline}\n"
                                f"Location: {lead.location}\n\n"
                                "Rewrite the message to be personalized for this recipient:"
                            ),
                        ),
                    ]
                    response = await self.llm_provider.complete(personalize_prompt)
                    if response.content:
                        msg = response.content.strip()
                except Exception:
                    pass  # Fall back to template version

            # Send via LinkedIn provider
            try:
                result = await self.linkedin_provider.send_message(
                    lead.linkedin_profile_id, msg
                )
                if result.success:
                    sent += 1
                    details.append({"name": lead.name, "status": "sent"})

                    # Update DB
                    async with self.db.session() as session:
                        lead_repo = LeadRepository(session)
                        msg_repo = MessageRepository(session)
                        await lead_repo.update_lead_status(cl.id, LeadStatus.contacted)
                        await msg_repo.record_message(
                            campaign_lead_id=cl.id,
                            content=msg,
                            direction=MessageDirection.outbound,
                            message_type=(
                                MessageType.custom if personalize else MessageType.template
                            ),
                        )
                else:
                    failed += 1
                    details.append({
                        "name": lead.name,
                        "status": "failed",
                        "error": result.error,
                    })
            except Exception as e:
                failed += 1
                details.append({"name": lead.name, "status": "failed", "error": str(e)})

        return ToolResult(
            output={
                "sent": sent,
                "failed": failed,
                "total": sent + failed,
                "personalized": personalize,
                "details": details,
            }
        )
