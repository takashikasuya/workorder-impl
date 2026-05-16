"""FUN-WO-001: Estimate 承認 → WorkOrder 自動生成のユニットテスト。"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

import httpx
import respx
from gutp.schemas.ticket import Estimate, EstimateStatus
from gutp_wo_manager.main import _auto_create_work_order

TICKET_BASE = "http://ticket-manager:8000"

TICKET_JSON = {
    "ticket_id": "t-001",
    "title": "空調設備の異常",
    "ticket_status": "Open",
    "addresses_issue_ids": [],
    "priority": 50,
    "due_at": None,
    "budget": None,
    "currency": "JPY",
    "description": "空調が停止しています",
    "estimated_cost": None,
    "actual_cost": None,
    "created_at": "2024-01-01T00:00:00",
}

ESTIMATE = Estimate(
    estimate_id="e-001",
    ticket_id="t-001",
    title="空調修理見積",
    estimated_cost=Decimal("150000"),
    estimated_duration="P2D",
    estimate_status=EstimateStatus.APPROVED,
    description="部品交換が必要",
)


@respx.mock
async def test_estimate_approved_creates_work_order():
    """有効な Ticket → WO が生成され wo.assigned が publish される。"""
    respx.get(f"{TICKET_BASE}/tickets/t-001").mock(
        return_value=httpx.Response(200, json=TICKET_JSON)
    )
    mock_nc = AsyncMock()

    async with httpx.AsyncClient(base_url=TICKET_BASE) as client:
        wo = await _auto_create_work_order(ESTIMATE, client, mock_nc)

    assert wo is not None
    assert wo.ticket_id == "t-001"
    assert wo.title == "空調設備の異常"
    assert wo.work_order_type == "CorrectiveMaintenance"
    mock_nc.publish.assert_awaited_once()
    subject = mock_nc.publish.call_args[0][0]
    assert subject == "wo.assigned"


@respx.mock
async def test_estimate_approved_ticket_not_found():
    """Ticket が 404 → WO を生成せず publish もしない。"""
    respx.get(f"{TICKET_BASE}/tickets/t-001").mock(return_value=httpx.Response(404))
    mock_nc = AsyncMock()

    async with httpx.AsyncClient(base_url=TICKET_BASE) as client:
        wo = await _auto_create_work_order(ESTIMATE, client, mock_nc)

    assert wo is None
    mock_nc.publish.assert_not_called()


@respx.mock
async def test_estimate_approved_ticket_service_error():
    """ticket-manager が 503 → WO を生成せず、例外を伝播させない。"""
    respx.get(f"{TICKET_BASE}/tickets/t-001").mock(return_value=httpx.Response(503))
    mock_nc = AsyncMock()

    async with httpx.AsyncClient(base_url=TICKET_BASE) as client:
        wo = await _auto_create_work_order(ESTIMATE, client, mock_nc)

    assert wo is None
    mock_nc.publish.assert_not_called()


@respx.mock
async def test_estimate_approved_ticket_connection_error():
    """ticket-manager への接続失敗（RequestError）→ WO を生成せず例外を伝播させない。"""
    respx.get(f"{TICKET_BASE}/tickets/t-001").mock(side_effect=httpx.ConnectError("refused"))
    mock_nc = AsyncMock()

    async with httpx.AsyncClient(base_url=TICKET_BASE) as client:
        wo = await _auto_create_work_order(ESTIMATE, client, mock_nc)

    assert wo is None
    mock_nc.publish.assert_not_called()
