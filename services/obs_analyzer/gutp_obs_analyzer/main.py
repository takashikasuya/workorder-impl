"""
CS-OBS-ANALYZER — 観測データ分析・評価ワーカー

機能: FUN-OBS-002 IoTEvent ルール評価 → Issue 生成判定
      FUN-OBS-004 Report トレンド分析
      FUN-OBS-007 未評価Report 滞留エスカレーション（IF-NOTIFY-001 publish, 未実装）

NATS から obs.iot-event.created / obs.report.created を購読し、
ルールエンジンで評価して Issue 生成が必要な場合は CS-ISSUE-MANAGER (IF-ISSUE-001) を呼ぶ。
"""

from __future__ import annotations

import asyncio
import os

import httpx
import nats
from gutp.events.subjects import OBS
from gutp.schemas.issue import IssueCreate, IssueType
from gutp.schemas.observation import IoTEvent, Report

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
ISSUE_MANAGER_URL = os.getenv("ISSUE_MANAGER_URL", "http://issue-manager:8000")


async def evaluate_iot_event(event: IoTEvent) -> IssueCreate | None:
    """ルールエンジン — IoTEvent を評価して Issue 生成要否を判定する (FUN-OBS-002)。

    TODO: 閾値・ルール定義を設定ファイルから読み込む。
    """
    # 最低限のデモルール: eventState が "ACTIVE" なら Issue を生成
    if event.event_state and event.event_state.upper() == "ACTIVE":
        return IssueCreate(
            title=f"[自動] {event.iot_event_type} アラーム検知",
            issue_type=IssueType.FACILITY_ASSET,
            derived_from_id=event.iot_event_id,
            derived_from_type="IoTEvent",
            is_standard=False,
        )
    return None


async def main() -> None:
    nc = await nats.connect(NATS_URL)
    async with httpx.AsyncClient(base_url=ISSUE_MANAGER_URL) as client:

        async def on_iot_event(msg: nats.aio.msg.Msg) -> None:
            event = IoTEvent.model_validate_json(msg.data)
            issue_data = await evaluate_iot_event(event)
            if issue_data:
                await client.post("/issues", content=issue_data.model_dump_json())

        async def on_report(msg: nats.aio.msg.Msg) -> None:
            _report = Report.model_validate_json(msg.data)
            # TODO: トレンド分析ロジック (FUN-OBS-004)

        await nc.subscribe(OBS.IOT_EVENT_CREATED, cb=on_iot_event)
        await nc.subscribe(OBS.REPORT_CREATED, cb=on_report)

        print("obs-analyzer: listening on NATS")
        try:
            await asyncio.Future()  # run forever
        finally:
            await nc.drain()


if __name__ == "__main__":
    asyncio.run(main())
