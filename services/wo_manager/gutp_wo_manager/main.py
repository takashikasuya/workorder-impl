"""
CS-WO-MANAGER — WorkOrder 管理サービス

機能: FUN-WO-001 WO 自動発行（Estimate承認後）
      FUN-WO-002 WO 手動発行
      FUN-WO-003 WO 参照
      FUN-WO-004 ServiceTask 完了報告
      FUN-WO-005 WO 完了自動遷移（全Task完了）
      FUN-WO-006 Booking 管理
      FUN-WO-007 緊急WO即時発行（未実装）

提供: IF-WO-001 (REST CRUD),
      IF-WO-002 (NATS 通知イベント: wo.assigned / wo.emergency.completed, ADR-003)
購読: IF-TICKET-002 (NATS ticket.estimate.approved) — WO 自動発行トリガー
備考: FUN-WO-007 / InProgress自動遷移 / Booking conflicted は未実装
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import nats
from fastapi import FastAPI, HTTPException
from gutp.events.subjects import TICKET
from gutp.schemas.ticket import Estimate
from gutp.schemas.workorder import (
    Booking,
    BookingCreate,
    ServiceTask,
    WorkOrder,
    WorkOrderCreate,
    WorkOrderStatus,
)

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")

_nc: nats.aio.client.Client | None = None
_work_orders: dict[str, WorkOrder] = {}
_tasks: dict[str, ServiceTask] = {}
_bookings: dict[str, Booking] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _nc
    _nc = await nats.connect(NATS_URL)

    async def on_estimate_approved(msg: nats.aio.msg.Msg) -> None:
        """Estimate 承認イベントを受信して WorkOrder 自動発行フローを起動する (FUN-WO-001)。"""
        estimate = Estimate.model_validate_json(msg.data)
        # TODO: Ticket から WorkOrder を自動生成するロジックを実装する
        print(f"[wo-manager] estimate approved: {estimate.estimate_id} → ticket {estimate.ticket_id}")

    await _nc.subscribe(TICKET.ESTIMATE_APPROVED, cb=on_estimate_approved)
    yield
    await _nc.drain()


app = FastAPI(title="wo-manager", lifespan=lifespan)


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/work-orders", status_code=201)
async def create_work_order(body: WorkOrderCreate) -> WorkOrder:
    wo_id = str(uuid.uuid4())
    task_ids: list[str] = []
    for task_req in body.tasks:
        task = ServiceTask(
            task_id=str(uuid.uuid4()),
            work_order_id=wo_id,
            **task_req.model_dump(),
        )
        _tasks[task.task_id] = task
        task_ids.append(task.task_id)
    record = WorkOrder(
        work_order_id=wo_id,
        ticket_id=body.ticket_id,
        title=body.title,
        work_order_type=body.work_order_type,
        description=body.description,
        task_ids=task_ids,
    )
    _work_orders[wo_id] = record
    return record


@app.get("/work-orders/{wo_id}")
async def get_work_order(wo_id: str) -> WorkOrder:
    record = _work_orders.get(wo_id)
    if not record:
        raise HTTPException(404, detail="WorkOrder not found")
    return record


@app.patch("/work-orders/{wo_id}/tasks/{task_id}/complete")
async def complete_task(wo_id: str, task_id: str) -> WorkOrder:
    wo = _work_orders.get(wo_id)
    task = _tasks.get(task_id)
    if not wo or not task:
        raise HTTPException(404)
    task.is_completed = True
    task.completed_at = datetime.utcnow()
    # 全 ServiceTask が完了したら WorkOrder を Completed に自動更新 (FUN-WO-005)
    if all(_tasks[tid].is_completed for tid in wo.task_ids):
        wo.work_order_status = WorkOrderStatus.COMPLETED
        wo.done_at = datetime.utcnow()
    return wo


@app.post("/bookings", status_code=201)
async def create_booking(body: BookingCreate) -> Booking:
    record = Booking(booking_id=str(uuid.uuid4()), **body.model_dump())
    _bookings[record.booking_id] = record
    return record
