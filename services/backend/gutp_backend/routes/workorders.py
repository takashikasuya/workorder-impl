"""IF-WO-001/002 — WorkOrder 管理 (from wo_manager)"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from gutp.events.subjects import WO
from gutp.schemas.ticket import Estimate
from gutp.schemas.workorder import (
    Booking,
    BookingCreate,
    BookingStatus,
    EmergencyWorkOrderCreate,
    ServiceTask,
    ServiceTaskCreate,
    WorkOrder,
    WorkOrderCreate,
    WorkOrderStatus,
)

from .. import state

logger = logging.getLogger(__name__)
router = APIRouter(tags=["workorders"])


def _build_work_order(body: WorkOrderCreate) -> WorkOrder:
    wo_id = str(uuid.uuid4())
    task_ids: list[str] = []
    for task_req in body.tasks:
        task = ServiceTask(task_id=str(uuid.uuid4()), work_order_id=wo_id, **task_req.model_dump())
        state.service_tasks[task.task_id] = task
        task_ids.append(task.task_id)
    record = WorkOrder(
        work_order_id=wo_id,
        ticket_id=body.ticket_id,
        title=body.title,
        work_order_type=body.work_order_type,
        description=body.description,
        task_ids=task_ids,
    )
    state.work_orders[wo_id] = record
    return record


async def on_estimate_approved(estimate: Estimate) -> WorkOrder | None:
    """Estimate 承認で WorkOrder を自動生成し通知する (FUN-WO-001)."""
    ticket = state.tickets.get(estimate.ticket_id)
    if not ticket:
        logger.warning("ticket %s not found, skipping WO creation", estimate.ticket_id)
        return None
    wo = _build_work_order(WorkOrderCreate(
        ticket_id=ticket.ticket_id,
        title=ticket.title,
        work_order_type="CorrectiveMaintenance",
        description=estimate.description,
    ))
    from ..tasks.notify import dispatch
    await dispatch(WO.ASSIGNED, wo.model_dump_json().encode())
    logger.info("wo.assigned: %s (ticket=%s)", wo.work_order_id, ticket.ticket_id)
    return wo


@router.post("/work-orders", status_code=201)
async def create_work_order(body: WorkOrderCreate) -> WorkOrder:
    return _build_work_order(body)


@router.post("/work-orders/emergency", status_code=201)
async def create_emergency_work_order(body: EmergencyWorkOrderCreate) -> WorkOrder:
    wo_id = str(uuid.uuid4())
    task_ids: list[str] = []
    for task_req in body.tasks:
        task = ServiceTask(task_id=str(uuid.uuid4()), work_order_id=wo_id, **task_req.model_dump())
        state.service_tasks[task.task_id] = task
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
    state.work_orders[wo_id] = wo
    from ..tasks.notify import dispatch
    await dispatch(WO.ASSIGNED, wo.model_dump_json().encode())
    logger.info("emergency wo created: %s", wo_id)
    return wo


@router.get("/work-orders")
async def list_work_orders() -> list[WorkOrder]:
    return list(state.work_orders.values())


@router.get("/work-orders/{wo_id}")
async def get_work_order(wo_id: str) -> WorkOrder:
    record = state.work_orders.get(wo_id)
    if not record:
        raise HTTPException(404, detail="WorkOrder not found")
    return record


@router.post("/work-orders/{wo_id}/tasks", status_code=201)
async def add_task(wo_id: str, body: ServiceTaskCreate) -> WorkOrder:
    wo = state.work_orders.get(wo_id)
    if not wo:
        raise HTTPException(404, detail="WorkOrder not found")
    if wo.work_order_status == WorkOrderStatus.COMPLETED:
        raise HTTPException(409, detail="Completed WorkOrder にタスクを追加できません")
    task = ServiceTask(task_id=str(uuid.uuid4()), work_order_id=wo_id, **body.model_dump())
    state.service_tasks[task.task_id] = task
    wo.task_ids.append(task.task_id)
    return wo


@router.patch("/work-orders/{wo_id}/tasks/{task_id}/complete")
async def complete_task(wo_id: str, task_id: str) -> WorkOrder:
    wo = state.work_orders.get(wo_id)
    task = state.service_tasks.get(task_id)
    if not wo or not task:
        raise HTTPException(404)
    if wo.work_order_status == WorkOrderStatus.OPEN:
        wo.work_order_status = WorkOrderStatus.IN_PROGRESS
        wo.started_at = datetime.utcnow()
    task.is_completed = True
    task.completed_at = datetime.utcnow()
    if all(state.service_tasks[tid].is_completed for tid in wo.task_ids):
        wo.work_order_status = WorkOrderStatus.COMPLETED
        wo.done_at = datetime.utcnow()
    return wo


@router.patch("/work-orders/{wo_id}/complete-emergency")
async def complete_emergency_work_order(wo_id: str) -> WorkOrder:
    wo = state.work_orders.get(wo_id)
    if not wo:
        raise HTTPException(404, detail="WorkOrder not found")
    if wo.work_order_type != "EmergencyMaintenance":
        raise HTTPException(409, detail="WorkOrder is not an emergency work order")
    wo.work_order_status = WorkOrderStatus.COMPLETED
    wo.done_at = datetime.utcnow()
    from ..tasks.notify import dispatch
    await dispatch(WO.EMERGENCY_COMPLETED, wo.model_dump_json().encode())
    logger.info("emergency wo completed: %s", wo_id)
    return wo


def _bookings_overlap(wo_id: str, start: datetime, end: datetime) -> bool:
    for b in state.bookings.values():
        if b.work_order_id != wo_id:
            continue
        if start < b.scheduled_end and end > b.scheduled_start:
            return True
    return False


@router.post("/bookings", status_code=201)
async def create_booking(body: BookingCreate) -> Booking:
    if _bookings_overlap(body.work_order_id, body.scheduled_start, body.scheduled_end):
        raise HTTPException(409, detail="Booking conflict: overlapping time slot for this WorkOrder")
    record = Booking(booking_id=str(uuid.uuid4()), **body.model_dump())
    state.bookings[record.booking_id] = record
    return record


@router.patch("/bookings/{booking_id}/confirm")
async def confirm_booking(booking_id: str) -> Booking:
    booking = state.bookings.get(booking_id)
    if not booking:
        raise HTTPException(404, detail="Booking not found")
    if booking.booking_status != BookingStatus.TENTATIVE:
        raise HTTPException(409, detail="Only Tentative bookings can be confirmed")
    booking.booking_status = BookingStatus.CONFIRMED
    wo = state.work_orders.get(booking.work_order_id)
    if wo and wo.work_order_status == WorkOrderStatus.OPEN:
        wo.work_order_status = WorkOrderStatus.IN_PROGRESS
        wo.started_at = datetime.utcnow()
    return booking
