"""IF-TICKET-001 — Ticket / Estimate 管理 (from ticket_manager)"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from gutp.schemas.ticket import Estimate, EstimateCreate, EstimateStatus, Ticket, TicketCreate

from .. import state

router = APIRouter(tags=["tickets"])


@router.post("/tickets", status_code=201)
async def create_ticket(body: TicketCreate) -> Ticket:
    record = Ticket(ticket_id=str(uuid.uuid4()), **body.model_dump())
    state.tickets[record.ticket_id] = record
    return record


@router.get("/tickets")
async def list_tickets() -> list[Ticket]:
    return list(state.tickets.values())


@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str) -> Ticket:
    record = state.tickets.get(ticket_id)
    if not record:
        raise HTTPException(404, detail="Ticket not found")
    return record


@router.post("/estimates", status_code=201)
async def create_estimate(body: EstimateCreate) -> Estimate:
    if body.ticket_id not in state.tickets:
        raise HTTPException(404, detail="Ticket not found")
    record = Estimate(estimate_id=str(uuid.uuid4()), **body.model_dump())
    state.estimates[record.estimate_id] = record
    return record


@router.get("/tickets/{ticket_id}/estimates")
async def list_ticket_estimates(ticket_id: str) -> list[Estimate]:
    if ticket_id not in state.tickets:
        raise HTTPException(404, detail="Ticket not found")
    return [e for e in state.estimates.values() if e.ticket_id == ticket_id]


@router.patch("/estimates/{estimate_id}/approve")
async def approve_estimate(estimate_id: str) -> Estimate:
    record = state.estimates.get(estimate_id)
    if not record:
        raise HTTPException(404, detail="Estimate not found")
    record.estimate_status = EstimateStatus.APPROVED
    record.approved_at = datetime.utcnow()
    from .workorders import on_estimate_approved
    await on_estimate_approved(record)
    return record
