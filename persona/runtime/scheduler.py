"""Agent scheduler — APScheduler wrapper for recurring tasks."""

from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class AgentScheduler:
    """Wraps APScheduler for agent-managed recurring jobs.

    Usage:
        scheduler = AgentScheduler()
        scheduler.start()
        scheduler.schedule_recurring("job1", my_async_func, interval_weeks=2)
        scheduler.cancel("job1")
        scheduler.stop()
    """

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()

    def start(self) -> None:
        """Start the scheduler."""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("Agent scheduler started")

    def stop(self) -> None:
        """Shut down the scheduler gracefully."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Agent scheduler stopped")

    def schedule_recurring(
        self,
        job_id: str,
        func: Callable[..., Coroutine[Any, Any, Any]],
        interval_weeks: int = 1,
        **kwargs: Any,
    ) -> None:
        """Schedule an async function to run every N weeks."""
        trigger = IntervalTrigger(weeks=interval_weeks)
        # Remove existing job if present, then add
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)

        self._scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            kwargs=kwargs,
            replace_existing=True,
        )
        logger.info(f"Scheduled job '{job_id}' every {interval_weeks} week(s)")

    def cancel(self, job_id: str) -> None:
        """Cancel a scheduled job."""
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
            logger.info(f"Cancelled job '{job_id}'")

    def list_jobs(self) -> list[dict[str, Any]]:
        """List all scheduled jobs."""
        jobs = self._scheduler.get_jobs()
        return [
            {
                "id": job.id,
                "next_run_time": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger),
            }
            for job in jobs
        ]
