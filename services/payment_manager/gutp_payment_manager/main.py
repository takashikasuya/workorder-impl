"""
CS-PAYMENT-MANAGER — 支払い管理サービス (FUN-PAYMENT-001)

提供: IF-PAYMENT-001 (REST CRUD)
依存: IF-WO-001 (wo-manager) — 完了 WorkOrder の照会
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from gutp.schemas.payment import Payment, PaymentCreate, PaymentStatus

WO_MANAGER_URL = os.getenv("WO_MANAGER_URL", "http://wo-manager:8000")

_payments: dict[str, Payment] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="payment-manager", lifespan=lifespan)


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/payments", status_code=201)
async def create_payment(body: PaymentCreate) -> Payment:
    # WorkOrder の存在確認 (IF-WO-001)
    async with httpx.AsyncClient(base_url=WO_MANAGER_URL) as client:
        resp = await client.get(f"/work-orders/{body.applies_to_work_order_id}")
        if resp.status_code == 404:
            raise HTTPException(404, detail="WorkOrder not found")

    record = Payment(payment_id=str(uuid.uuid4()), **body.model_dump())
    _payments[record.payment_id] = record
    return record


@app.get("/payments/{payment_id}")
async def get_payment(payment_id: str) -> Payment:
    record = _payments.get(payment_id)
    if not record:
        raise HTTPException(404, detail="Payment not found")
    return record


@app.patch("/payments/{payment_id}/mark-paid")
async def mark_paid(payment_id: str) -> Payment:
    record = _payments.get(payment_id)
    if not record:
        raise HTTPException(404, detail="Payment not found")
    record.payment_status = PaymentStatus.PAID
    return record
