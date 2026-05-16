"""
CS-NOTIFY-DISPATCHER — 通知ディスパッチャー (FUN-NOTIFY-001)

購読: IF-WO-002    wo.assigned / wo.emergency.completed（CS-WO-MANAGER）
      IF-NOTIFY-001 obs.report.escalation（CS-OBS-ANALYZER）
提供: IF-NOTIFY-002 — 外部チャネルへのマルチチャネル配信境界

各業務CSが publish した通知イベントを購読し、NOTIFY_ADAPTER
（email|slack|webhook|push|sms）に従って外部チャネルへ配信する。
業務CSはチャネルを意識しない（配信責務の一元化・ADR-003 / REQ-SOS-018）。

NOTE: 本ファイルはアーキ同期によるスケルトン。
      実配信アダプタ・リトライ・配信履歴は未実装。
"""

from __future__ import annotations

import asyncio
import os

import nats

from gutp.events.subjects import OBS, WO

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
# IF-NOTIFY-002: 配信チャネル切り替え（email|slack|webhook|push|sms）
NOTIFY_ADAPTER = os.getenv("NOTIFY_ADAPTER", "email")


async def dispatch(topic: str, payload: bytes) -> None:
    """FUN-NOTIFY-001 — 受信イベントを NOTIFY_ADAPTER に従い配信する。

    TODO: adapter 実装（email=SMTP / slack=Webhook / webhook=HTTP /
          push=Push GW / sms=SMS GW）、リトライ、配信履歴記録。
    """
    print(f"notify-dispatcher[{NOTIFY_ADAPTER}] <- {topic}: {payload[:120]!r}")


async def main() -> None:
    nc = await nats.connect(NATS_URL)

    async def on_event(msg: nats.aio.msg.Msg) -> None:
        await dispatch(msg.subject, msg.data)

    # IF-WO-002（CS-WO-MANAGER） / IF-NOTIFY-001（CS-OBS-ANALYZER）
    await nc.subscribe(WO.ASSIGNED, cb=on_event)
    await nc.subscribe(WO.EMERGENCY_COMPLETED, cb=on_event)
    await nc.subscribe(OBS.REPORT_ESCALATION, cb=on_event)

    print(f"notify-dispatcher: listening (adapter={NOTIFY_ADAPTER})")
    try:
        await asyncio.Future()  # run forever
    finally:
        await nc.drain()


if __name__ == "__main__":
    asyncio.run(main())
