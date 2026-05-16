"""
CS-OBS-ANALYZER — 観測データ分析・評価ワーカー

機能: FUN-OBS-002 IoTEvent ルール評価 → Issue 生成判定
      FUN-OBS-004 Report トレンド分析
      FUN-OBS-007 未評価Report 滞留エスカレーション（IF-NOTIFY-001 publish）

NATS から obs.iot-event.created / obs.report.created / obs.report.evaluated を購読し、
ルールエンジンで評価して Issue 生成が必要な場合は CS-ISSUE-MANAGER (IF-ISSUE-001) を呼ぶ。
未評価 Report は ESCALATION_THRESHOLD_SEC 秒後に obs.report.escalation を publish する。
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime

import httpx
import nats
from gutp.events.subjects import OBS
from gutp.schemas.issue import IssueCreate, IssueType
from gutp.schemas.observation import IoTEvent, Report
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
ISSUE_MANAGER_URL = os.getenv("ISSUE_MANAGER_URL", "http://issue-manager:8000")
ESCALATION_THRESHOLD_SEC = int(os.getenv("ESCALATION_THRESHOLD_SEC", "1800"))
ESCALATION_CHECK_INTERVAL_SEC = int(os.getenv("ESCALATION_CHECK_INTERVAL_SEC", "60"))

_pending_reports: dict[str, tuple[Report, datetime]] = {}


class _ReportEvaluatedEvent(BaseModel):
    report_id: str


async def evaluate_iot_event(event: IoTEvent) -> IssueCreate | None:
    """ルールエンジン — IoTEvent を評価して Issue 生成要否を判定する (FUN-OBS-002)。

    TODO: 閾値・ルール定義を設定ファイルから読み込む。
    """
    if event.event_state and event.event_state.upper() == "ACTIVE":
        return IssueCreate(
            title=f"[自動] {event.iot_event_type} アラーム検知",
            issue_type=IssueType.FACILITY_ASSET,
            derived_from_id=event.iot_event_id,
            derived_from_type="IoTEvent",
            is_standard=False,
        )
    return None


async def _handle_report_created(report: Report) -> None:
    """obs.report.created 受信時、Report を pending キューに登録する (FUN-OBS-007)。"""
    _pending_reports[report.report_id] = (report, datetime.utcnow())
    logger.info("pending report registered: %s", report.report_id)


async def _handle_report_evaluated(report_id: str) -> None:
    """obs.report.evaluated 受信時、評価済み Report を pending キューから除去する (FUN-OBS-007)。"""
    if _pending_reports.pop(report_id, None) is not None:
        logger.info("pending report cleared (evaluated): %s", report_id)


async def _scan_and_escalate(nc: nats.aio.client.Client) -> None:
    """閾値超過の未評価 Report を検出して obs.report.escalation を publish する (FUN-OBS-007)。"""
    now = datetime.utcnow()
    to_escalate = [
        (rid, report)
        for rid, (report, received_at) in list(_pending_reports.items())
        if (now - received_at).total_seconds() >= ESCALATION_THRESHOLD_SEC
    ]
    for rid, report in to_escalate:
        await nc.publish(OBS.REPORT_ESCALATION, report.model_dump_json().encode())
        del _pending_reports[rid]
        logger.info("escalated report: %s", rid)


async def main() -> None:
    nc = await nats.connect(NATS_URL)
    async with httpx.AsyncClient(base_url=ISSUE_MANAGER_URL) as client:

        async def on_iot_event(msg: nats.aio.msg.Msg) -> None:
            try:
                event = IoTEvent.model_validate_json(msg.data)
                issue_data = await evaluate_iot_event(event)
                if issue_data:
                    await client.post("/issues", content=issue_data.model_dump_json())
            except Exception:
                logger.exception("obs.iot-event.created 処理失敗")

        async def on_report(msg: nats.aio.msg.Msg) -> None:
            try:
                report = Report.model_validate_json(msg.data)
                await _handle_report_created(report)
            except Exception:
                logger.exception("obs.report.created 処理失敗")

        async def on_report_evaluated(msg: nats.aio.msg.Msg) -> None:
            try:
                event = _ReportEvaluatedEvent.model_validate_json(msg.data)
                await _handle_report_evaluated(event.report_id)
            except Exception:
                logger.exception("obs.report.evaluated 処理失敗")

        async def _escalation_loop() -> None:
            while True:
                await asyncio.sleep(ESCALATION_CHECK_INTERVAL_SEC)
                await _scan_and_escalate(nc)

        await nc.subscribe(OBS.IOT_EVENT_CREATED, cb=on_iot_event)
        await nc.subscribe(OBS.REPORT_CREATED, cb=on_report)
        await nc.subscribe(OBS.REPORT_EVALUATED, cb=on_report_evaluated)
        asyncio.create_task(_escalation_loop())

        logger.info("obs-analyzer: listening on NATS")
        try:
            await asyncio.Future()
        finally:
            await nc.drain()


if __name__ == "__main__":
    asyncio.run(main())
