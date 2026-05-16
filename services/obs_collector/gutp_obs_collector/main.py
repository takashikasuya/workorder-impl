"""
CS-OBS-COLLECTOR — 観測データ収集サービス (FUN-OBS-001, FUN-OBS-003)

ビルOS からの IoTEvent / Report を REST コネクタで受信し、
永続化後に NATS トピックへ publish する (IF-OBS-003)。

コネクタ追加手順:
  ConnectorRegistry.register(YourConnector(on_event=handle_ingress)) を
  startup ハンドラで呼ぶだけでよい。
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import nats
from fastapi import FastAPI
from gutp.connectors.base import ConnectorRegistry, IngressEvent
from gutp.connectors.rest.router import make_rest_router
from gutp.events.subjects import OBS
from gutp.schemas.observation import IoTEvent, IoTEventCreate, Report, ReportCreate

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")

_nc: nats.aio.client.Client | None = None
_registry = ConnectorRegistry()

# ── インメモリストア（本番では DB に置き換える） ───────────────────────────────
_iot_events: dict[str, IoTEvent] = {}
_reports: dict[str, Report] = {}


async def handle_ingress(event: IngressEvent) -> None:
    """コネクタからの IngressEvent を永続化して NATS に publish する。"""
    if event.event_type == "IoTEvent":
        body = IoTEventCreate(**event.payload)
        record = IoTEvent(
            iot_event_id=str(uuid.uuid4()),
            received_at=datetime.utcnow(),
            **body.model_dump(),
        )
        _iot_events[record.iot_event_id] = record
        subject = OBS.IOT_EVENT_CREATED
        payload = record.model_dump_json()

    elif event.event_type == "Report":
        body = ReportCreate(**event.payload)
        record = Report(
            report_id=str(uuid.uuid4()),
            received_at=datetime.utcnow(),
            **body.model_dump(),
        )
        _reports[record.report_id] = record
        subject = OBS.REPORT_CREATED
        payload = record.model_dump_json()

    else:
        return

    if _nc:
        await _nc.publish(subject, payload.encode())


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _nc
    _nc = await nats.connect(NATS_URL)

    # REST コネクタを登録（gRPC 等を追加するにはここに追記）
    _registry.register(type("_RestConnector", (), {
        "name": "rest",
        "start": staticmethod(lambda: None),
        "stop": staticmethod(lambda: None),
    })())

    yield

    await _registry.stop_all()
    await _nc.drain()


app = FastAPI(title="obs-collector", lifespan=lifespan)
app.include_router(make_rest_router(on_event=handle_ingress))


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/iot-events/{iot_event_id}")
async def get_iot_event(iot_event_id: str) -> IoTEvent:
    from fastapi import HTTPException
    record = _iot_events.get(iot_event_id)
    if not record:
        raise HTTPException(404, detail="IoTEvent not found")
    return record


@app.get("/reports/{report_id}")
async def get_report(report_id: str) -> Report:
    from fastapi import HTTPException
    record = _reports.get(report_id)
    if not record:
        raise HTTPException(404, detail="Report not found")
    return record
