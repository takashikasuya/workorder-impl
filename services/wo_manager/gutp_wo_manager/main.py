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
備考: FUN-WO-007 緊急WO即時発行は未実装
"""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import httpx
import nats
from fastapi import FastAPI, HTTPException
from gutp.events.subjects import TICKET, WO
from gutp.schemas.ticket import Estimate, Ticket
from gutp.schemas.workorder import (
    Booking,
    BookingCreate,
    BookingStatus,
    EmergencyWorkOrderCreate,
    ServiceTask,
    WorkOrder,
    WorkOrderCreate,
    WorkOrderStatus,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
TICKET_MANAGER_URL = os.getenv("TICKET_MANAGER_URL", "http://ticket-manager:8000")

_nc: nats.aio.client.Client | None = None
_http_client: httpx.AsyncClient | None = None
_work_orders: dict[str, WorkOrder] = {}
_tasks: dict[str, ServiceTask] = {}
_bookings: dict[str, Booking] = {}


def _build_work_order(body: WorkOrderCreate) -> WorkOrder:
    """WorkOrderCreate から WorkOrder を構築してインメモリに保存する。"""
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


async def _auto_create_work_order(
    estimate: Estimate,
    http_client: httpx.AsyncClient,
    nc: nats.aio.client.Client,
) -> WorkOrder | None:
    """Estimate 承認をもとに WorkOrder を自動生成し wo.assigned を publish する (FUN-WO-001)."""
    try:
        resp = await http_client.get(f"/tickets/{estimate.ticket_id}")
    except httpx.RequestError as exc:
        logger.warning("ticket-manager への接続失敗 (%s), WO 生成をスキップ", exc)
        return None
    if resp.status_code != 200:
        logger.warning("ticket %s fetch failed (%d), WO 生成をスキップ", estimate.ticket_id, resp.status_code)
        return None
    ticket = Ticket.model_validate(resp.json())
    wo = _build_work_order(
        WorkOrderCreate(
            ticket_id=ticket.ticket_id,
            title=ticket.title,
            work_order_type="CorrectiveMaintenance",
            description=estimate.description,
        )
    )
    await nc.publish(WO.ASSIGNED, wo.model_dump_json().encode())
    logger.info("wo.assigned published: %s (ticket=%s)", wo.work_order_id, ticket.ticket_id)
    return wo


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _nc, _http_client
    _nc = await nats.connect(NATS_URL)
    _http_client = httpx.AsyncClient(base_url=TICKET_MANAGER_URL)

    async def on_estimate_approved(msg: nats.aio.msg.Msg) -> None:
        """Estimate 承認イベントを受信して WorkOrder 自動発行フローを起動する (FUN-WO-001)。"""
        estimate = Estimate.model_validate_json(msg.data)
        await _auto_create_work_order(estimate, _http_client, _nc)

    await _nc.subscribe(TICKET.ESTIMATE_APPROVED, cb=on_estimate_approved)
    yield
    await _http_client.aclose()
    await _nc.drain()


app = FastAPI(title="wo-manager", lifespan=lifespan)


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/work-orders", status_code=201)
async def create_work_order(body: WorkOrderCreate) -> WorkOrder:
    return _build_work_order(body)


@app.post("/work-orders/emergency", status_code=201)
async def create_emergency_work_order(body: EmergencyWorkOrderCreate) -> WorkOrder:
    """Ticket 不要で即時 IN_PROGRESS の WO を作成し wo.assigned を publish する (FUN-WO-007)。"""
    wo_id = str(uuid.uuid4())
    task_ids: list[str] = []
    for task_req in body.tasks:
        task = ServiceTask(task_id=str(uuid.uuid4()), work_order_id=wo_id, **task_req.model_dump())
        _tasks[task.task_id] = task
        task_ids.append(task.task_id)
    wo = WorkOrder(
        work_order_id=wo_id,
        ticket_id=body.ticket_id,
        title=body.reason,
        work_order_type="EmergencyMaintenance",
        work_order_status=WorkOrderStatus.IN_PROGRESS,
        started_at=datetime.utcnow(),
        task_ids=task_ids,
    )
    _work_orders[wo_id] = wo
    await _nc.publish(WO.ASSIGNED, wo.model_dump_json().encode())
    logger.info("emergency wo created and wo.assigned published: %s", wo_id)
    return wo


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
    # WO が未着手なら作業開始として IN_PROGRESS に遷移 (FUN-WO-004)
    if wo.work_order_status == WorkOrderStatus.OPEN:
        wo.work_order_status = WorkOrderStatus.IN_PROGRESS
        wo.started_at = datetime.utcnow()
    task.is_completed = True
    task.completed_at = datetime.utcnow()
    # 全 ServiceTask が完了したら WorkOrder を Completed に自動更新 (FUN-WO-005)
    if all(_tasks[tid].is_completed for tid in wo.task_ids):
        wo.work_order_status = WorkOrderStatus.COMPLETED
        wo.done_at = datetime.utcnow()
    return wo


def _bookings_overlap(wo_id: str, start: datetime, end: datetime) -> bool:
    """指定 WO の既存 Booking と時間帯が重複するか判定する。"""
    for b in _bookings.values():
        if b.work_order_id != wo_id:
            continue
        if start < b.scheduled_end and end > b.scheduled_start:
            return True
    return False


@app.post("/bookings", status_code=201)
async def create_booking(body: BookingCreate) -> Booking:
    if _bookings_overlap(body.work_order_id, body.scheduled_start, body.scheduled_end):
        raise HTTPException(409, detail="Booking conflict: overlapping time slot for this WorkOrder")
    record = Booking(booking_id=str(uuid.uuid4()), **body.model_dump())
    _bookings[record.booking_id] = record
    return record


@app.patch("/work-orders/{wo_id}/complete-emergency")
async def complete_emergency_work_order(wo_id: str) -> WorkOrder:
    """緊急 WO を完了状態にして wo.emergency.completed を publish する (FUN-WO-007)。"""
    wo = _work_orders.get(wo_id)
    if not wo:
        raise HTTPException(404, detail="WorkOrder not found")
    if wo.work_order_type != "EmergencyMaintenance":
        raise HTTPException(409, detail="WorkOrder is not an emergency work order")
    wo.work_order_status = WorkOrderStatus.COMPLETED
    wo.done_at = datetime.utcnow()
    await _nc.publish(WO.EMERGENCY_COMPLETED, wo.model_dump_json().encode())
    logger.info("emergency wo completed and wo.emergency.completed published: %s", wo_id)
    return wo


@app.patch("/bookings/{booking_id}/confirm")
async def confirm_booking(booking_id: str) -> Booking:
    """Booking を確定し、対応する WO を IN_PROGRESS に遷移させる (FUN-WO-006)。"""
    booking = _bookings.get(booking_id)
    if not booking:
        raise HTTPException(404, detail="Booking not found")
    if booking.booking_status != BookingStatus.TENTATIVE:
        raise HTTPException(409, detail="Only Tentative bookings can be confirmed")
    booking.booking_status = BookingStatus.CONFIRMED
    wo = _work_orders.get(booking.work_order_id)
    if wo and wo.work_order_status == WorkOrderStatus.OPEN:
        wo.work_order_status = WorkOrderStatus.IN_PROGRESS
        wo.started_at = datetime.utcnow()
    return booking
