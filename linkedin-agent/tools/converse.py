"""Converse with LinkedIn leads who have replied."""

from __future__ import annotations

from typing import Any

from persona.core.tool import Tool, ToolResult


class ConverseTool(Tool):
    name = "converse_with_lead"
    description = (
        "Reply to a LinkedIn lead who has responded to your outreach. "
        "Uses AI to generate a contextual reply based on the conversation history, "
        "or sends a custom message you provide."
    )
    parameters = {
        "type": "object",
        "properties": {
            "conversation_id": {
                "type": "string",
                "description": "LinkedIn conversation ID to reply to",
            },
            "message": {
                "type": "string",
                "description": "Message to send. If omitted, AI will generate an appropriate reply.",
            },
            "auto_reply": {
                "type": "boolean",
                "description": "If true and no message provided, AI generates the reply. Default false.",
                "default": False,
            },
        },
        "required": ["conversation_id"],
    }

    linkedin_provider: Any = None
    db: Any = None
    llm_provider: Any = None

    async def execute(self, **kwargs: Any) -> ToolResult:
        from db.models import MessageDirection, MessageType
        from db.repository import MessageRepository
        from persona.core.response import Message as LLMMessage

        conversation_id = kwargs["conversation_id"]
        message = kwargs.get("message")
        auto_reply = kwargs.get("auto_reply", False)

        if not self.linkedin_provider:
            return ToolResult(output=None, error="LinkedIn provider not configured")

        # If no message provided and auto_reply is on, generate one with LLM
        if not message and auto_reply and self.llm_provider:
            # Fetch conversation context
            try:
                conversations = await self.linkedin_provider.get_conversations()
                conv = next(
                    (c for c in conversations if c.conversation_id == conversation_id),
                    None,
                )
                if not conv:
                    return ToolResult(
                        output=None,
                        error=f"Conversation {conversation_id} not found",
                    )

                # Build conversation history for LLM
                history = "\n".join(
                    f"{'You' if m.is_outbound else conv.participant_name}: {m.content}"
                    for m in conv.messages
                )

                messages = [
                    LLMMessage(
                        role="system",
                        content=(
                            "You are a professional sales development representative. "
                            "Generate a concise, friendly reply to continue this LinkedIn conversation. "
                            "Keep the reply under 200 characters. Be professional and value-driven. "
                            "If the lead seems interested, try to suggest a call or meeting."
                        ),
                    ),
                    LLMMessage(
                        role="user",
                        content=(
                            f"Conversation with {conv.participant_name}:\n\n"
                            f"{history}\n\n"
                            "Generate the next reply:"
                        ),
                    ),
                ]
                response = await self.llm_provider.complete(messages)
                message = (response.content or "").strip()
            except Exception as e:
                return ToolResult(
                    output=None,
                    error=f"Failed to generate auto-reply: {e}",
                )

        if not message:
            return ToolResult(
                output=None,
                error="No message provided and auto_reply is disabled",
            )

        # Send the reply
        try:
            result = await self.linkedin_provider.reply_to_conversation(
                conversation_id, message
            )
        except Exception as e:
            return ToolResult(output=None, error=f"Failed to send reply: {e}")

        if not result.success:
            return ToolResult(output=None, error=result.error)

        # Record outbound message in DB
        if self.db:
            async with self.db.session() as session:
                msg_repo = MessageRepository(session)
                # Find the campaign_lead by conversation_id
                from sqlalchemy import select
                from db.models import ConversationRecord

                conv_result = await session.execute(
                    select(ConversationRecord).where(
                        ConversationRecord.linkedin_conversation_id == conversation_id
                    )
                )
                conv_record = conv_result.scalar_one_or_none()
                if conv_record:
                    await msg_repo.record_message(
                        campaign_lead_id=conv_record.campaign_lead_id,
                        content=message,
                        direction=MessageDirection.outbound,
                        message_type=MessageType.custom,
                    )

        return ToolResult(
            output={
                "conversation_id": conversation_id,
                "message_sent": message,
                "message_id": result.message_id,
                "status": "sent",
            }
        )
