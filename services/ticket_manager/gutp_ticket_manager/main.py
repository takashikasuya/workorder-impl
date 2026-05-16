"""
CS-TICKET-MANAGER — Ticket / Estimate 管理サービス

機能: FUN-TICKET-001 Ticket 起票
      FUN-TICKET-002 Estimate 起票
      FUN-TICKET-003 Estimate 承認（NATS publish → WO 自動発行トリガー）

提供: IF-TICKET-001 (REST CRUD), IF-TICKET-002 (NATS ticket.estimate.approved)
購読: IF-ISSUE-002 (NATS issue.created) — Issue 生成イベント受信
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import nats
from fastapi import FastAPI, HTTPException
from gutp.events.subjects import ISSUE, TICKET
from gutp.schemas.ticket import (
    Estimate,
    EstimateCreate,
    EstimateStatus,
    Ticket,
    TicketCreate,
)

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")

_nc: nats.aio.client.Client | None = None
_tickets: dict[str, Ticket] = {}
_estimates: dict[str, Estimate] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _nc
    _nc = await nats.connect(NATS_URL)

    async def on_issue_created(msg: nats.aio.msg.Msg) -> None:
        # Issue 生成通知を受信 — 必要に応じて自動 Ticket 起票（将来拡張）
        pass

    await _nc.subscribe(ISSUE.CREATED, cb=on_issue_created)
    yield
    await _nc.drain()


app = FastAPI(title="ticket-manager", lifespan=lifespan)


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/tickets", status_code=201)
async def create_ticket(body: TicketCreate) -> Ticket:
    record = Ticket(ticket_id=str(uuid.uuid4()), **body.model_dump())
    _tickets[record.ticket_id] = record
    return record


@app.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str) -> Ticket:
    record = _tickets.get(ticket_id)
    if not record:
        raise HTTPException(404, detail="Ticket not found")
    return record


@app.post("/estimates", status_code=201)
async def create_estimate(body: EstimateCreate) -> Estimate:
    if body.ticket_id not in _tickets:
        raise HTTPException(404, detail="Ticket not found")
    record = Estimate(estimate_id=str(uuid.uuid4()), **body.model_dump())
    _estimates[record.estimate_id] = record
    return record


@app.patch("/estimates/{estimate_id}/approve")
async def approve_estimate(estimate_id: str) -> Estimate:
    record = _estimates.get(estimate_id)
    if not record:
        raise HTTPException(404, detail="Estimate not found")
    record.estimate_status = EstimateStatus.APPROVED
    record.approved_at = datetime.utcnow()
    if _nc:
        await _nc.publish(TICKET.ESTIMATE_APPROVED, record.model_dump_json().encode())
    return record
