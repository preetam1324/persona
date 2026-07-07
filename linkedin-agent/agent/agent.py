"""LinkedIn Lead Generation Agent — custom agent subclass."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from persona.core.agent import Agent

if TYPE_CHECKING:
    from persona.core.config import PersonaConfig

logger = logging.getLogger(__name__)


class LinkedInAgent(Agent):
    """Custom agent that initializes LinkedIn provider, database, and scheduler.

    This agent wires up:
    - A pluggable LinkedIn API provider (mock, rapidapi, etc.)
    - PostgreSQL database for persistent lead/campaign/message storage
    - APScheduler for recurring campaign execution
    - Dependency injection into tools (provider, db, llm references)
    """

    def __init__(self, config: "PersonaConfig", secrets: dict[str, str], data_dir: Path):
        super().__init__(config, secrets, data_dir)
        self.linkedin_provider = None
        self.db = None
        self.scheduler = None

    def load(self) -> None:
        """Called once at startup — initialize LinkedIn provider, DB, and scheduler."""
        import asyncio

        # 1. Initialize LinkedIn provider
        linkedin_type = self.secrets.get("LINKEDIN_PROVIDER_TYPE", "mock")
        from providers import create_linkedin_provider

        self.linkedin_provider = create_linkedin_provider(linkedin_type, self.secrets)
        logger.info(f"LinkedIn provider initialized: {linkedin_type}")

        # 2. Initialize database (if configured)
        db_url = self.secrets.get("DATABASE_URL", "")
        if db_url:
            from persona.storage.database import Database

            self.db = Database(url=db_url)

            # Create tables — run sync in the event loop if available, otherwise create new loop
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._init_db())
            except RuntimeError:
                asyncio.run(self._init_db())

            logger.info("Database initialized")
        else:
            logger.warning(
                "DATABASE_URL not set — running without persistent storage. "
                "Lead data will not be persisted across restarts."
            )

        # 3. Initialize scheduler
        scheduler_config = self.config.runtime.scheduler
        if scheduler_config and scheduler_config.enabled:
            from persona.runtime.scheduler import AgentScheduler

            self.scheduler = AgentScheduler()
            self.scheduler.start()
            logger.info("Agent scheduler started")

            # Restore scheduled jobs from DB if available
            if self.db:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._restore_scheduled_jobs())
                except RuntimeError:
                    asyncio.run(self._restore_scheduled_jobs())

        # 4. Create data/exports directory
        exports_dir = self.data_dir / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)

    async def _init_db(self) -> None:
        """Initialize database tables."""
        from db.models import Base

        await self.db.init(Base)

    async def _restore_scheduled_jobs(self) -> None:
        """Restore recurring jobs for active campaigns from the database."""
        if not self.db or not self.scheduler:
            return

        from db.repository import CampaignRepository

        async with self.db.session() as session:
            repo = CampaignRepository(session)
            active_campaigns = await repo.list_active()

            for campaign in active_campaigns:
                self.scheduler.schedule_recurring(
                    job_id=f"campaign_{campaign.id}",
                    func=self._run_campaign_cycle,
                    interval_weeks=campaign.interval_weeks,
                    campaign_id=campaign.id,
                )
                logger.info(
                    f"Restored scheduled job for campaign '{campaign.name}' "
                    f"(every {campaign.interval_weeks} week(s))"
                )

    async def _run_campaign_cycle(self, campaign_id: str) -> None:
        """Automated campaign cycle: search for leads + check for replies."""
        if not self.db:
            return

        from db.repository import CampaignRepository

        async with self.db.session() as session:
            repo = CampaignRepository(session)
            campaign = await repo.get(campaign_id)
            if not campaign or campaign.status.value != "active":
                return

        criteria = campaign.criteria_json
        logger.info(f"Running campaign cycle for '{campaign.name}'")

        # Auto-search for new leads
        if self.linkedin_provider and criteria:
            from providers.models import SearchCriteria

            search_criteria = SearchCriteria(**criteria)
            try:
                profiles = await self.linkedin_provider.search_people(search_criteria)
                if profiles:
                    from db.repository import LeadRepository

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
                    logger.info(
                        f"Campaign '{campaign.name}': found {len(profiles)} leads"
                    )
            except Exception as e:
                logger.error(f"Campaign search failed: {e}")

        # Auto-check for replies
        try:
            conversations = await self.linkedin_provider.get_conversations()
            if conversations:
                from db.models import LeadStatus, MessageDirection, MessageType
                from db.repository import LeadRepository, MessageRepository

                async with self.db.session() as session:
                    lead_repo = LeadRepository(session)
                    msg_repo = MessageRepository(session)
                    contacted = await lead_repo.get_campaign_leads(
                        campaign_id, status=LeadStatus.contacted
                    )
                    for cl, lead in contacted:
                        for conv in conversations:
                            if conv.participant_id == lead.linkedin_profile_id:
                                await lead_repo.update_lead_status(
                                    cl.id, LeadStatus.replied
                                )
                                for msg in conv.messages:
                                    if not msg.is_outbound:
                                        await msg_repo.record_message(
                                            campaign_lead_id=cl.id,
                                            content=msg.content,
                                            direction=MessageDirection.inbound,
                                            message_type=MessageType.custom,
                                        )
                                await msg_repo.upsert_conversation(
                                    campaign_lead_id=cl.id,
                                    linkedin_conversation_id=conv.conversation_id,
                                    last_message_at=conv.last_message_at,
                                )
        except Exception as e:
            logger.error(f"Campaign reply-check failed: {e}")

    def inject_dependencies(self, tools_registry: "ToolRegistry", provider: "LLMProvider") -> None:
        """Inject LinkedIn provider, DB, scheduler, and LLM into tools that need them.

        Called by the agent runtime after tools are loaded.
        """
        for tool in tools_registry.list_tools():
            if hasattr(tool, "linkedin_provider"):
                tool.linkedin_provider = self.linkedin_provider
            if hasattr(tool, "db"):
                tool.db = self.db
            if hasattr(tool, "scheduler"):
                tool.scheduler = self.scheduler
            if hasattr(tool, "llm_provider"):
                tool.llm_provider = provider

        logger.info("Dependencies injected into tools")
