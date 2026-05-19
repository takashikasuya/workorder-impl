"""FUN-SCHEDULE-001/002 — 予防保全スケジューラー (from wo_scheduler)"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

from gutp.schemas.issue import Issue
from gutp.schemas.ticket import Estimate, EstimateStatus, Ticket

from .. import state

logger = logging.getLogger(__name__)

SCHEDULE_INTERVAL_SEC = int(os.getenv("SCHEDULE_INTERVAL_SEC", "300"))


async def run_cycle() -> None:
    """due なスケジュールを評価し Issue→Ticket→Estimate チェーンを発行する (FUN-SCHEDULE-001)."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    due = [s for s in state.schedules.values() if s.next_trigger_at <= now]
    for sched in due:
        await _trigger(sched, now)


async def _trigger(sched, now: datetime) -> None:

    issue = Issue(
        issue_id=str(uuid.uuid4()),
        title=sched.title,
        issue_type=sched.issue_type,
        derived_from_id=None,
        derived_from_type=None,
        description=f"予防保全スケジュール '{sched.title}' による自動起票",
        is_standard=True,
    )
    state.issues[issue.issue_id] = issue

    ticket = Ticket(
        ticket_id=str(uuid.uuid4()),
        title=sched.title,
        addresses_issue_ids=[issue.issue_id],
    )
    state.tickets[ticket.ticket_id] = ticket

    estimate = Estimate(
        estimate_id=str(uuid.uuid4()),
        ticket_id=ticket.ticket_id,
        title=sched.title,
        estimated_cost="0",
        estimated_duration="P1D",
    )
    state.estimates[estimate.estimate_id] = estimate

    estimate.estimate_status = EstimateStatus.APPROVED
    estimate.approved_at = now

    from ..routes.workorders import on_estimate_approved
    await on_estimate_approved(estimate)

    sched.last_triggered_at = now
    sched.next_trigger_at = now + timedelta(days=sched.interval_days)
    logger.info("schedule '%s' triggered", sched.schedule_id)


async def cycle_loop() -> None:
    while True:
        await asyncio.sleep(SCHEDULE_INTERVAL_SEC)
        try:
            await run_cycle()
        except Exception as exc:
            logger.warning("cycle_loop error: %s", exc)
