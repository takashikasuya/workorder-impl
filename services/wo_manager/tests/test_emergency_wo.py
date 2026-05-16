"""FUN-WO-007: 緊急 WO 即時発行エンドポイントのユニットテスト。"""

from __future__ import annotations

import gutp_wo_manager.main as m
from gutp.events.subjects import WO

EMERGENCY_BODY = {
    "reason": "エレベーター緊急停止",
    "tasks": [],
}

EMERGENCY_BODY_WITH_TICKET = {
    "reason": "空調緊急故障",
    "ticket_id": "t-emergency-001",
    "tasks": [{"title": "現地確認", "description": None}],
}


async def test_emergency_wo_returns_in_progress(ac, mock_nc):
    """POST /work-orders/emergency → 201、IN_PROGRESS かつ started_at が設定される。"""
    m._nc = mock_nc
    resp = await ac.post("/work-orders/emergency", json=EMERGENCY_BODY)
    assert resp.status_code == 201
    data = resp.json()
    assert data["work_order_status"] == "InProgress"
    assert data["started_at"] is not None


async def test_emergency_wo_ticket_id_optional(ac, mock_nc):
    """ticket_id なしで POST → 201、ticket_id が null。"""
    m._nc = mock_nc
    resp = await ac.post("/work-orders/emergency", json=EMERGENCY_BODY)
    assert resp.status_code == 201
    assert resp.json()["ticket_id"] is None


async def test_emergency_wo_with_ticket_id(ac, mock_nc):
    """ticket_id を指定して POST → レスポンスに ticket_id が反映される。"""
    m._nc = mock_nc
    resp = await ac.post("/work-orders/emergency", json=EMERGENCY_BODY_WITH_TICKET)
    assert resp.status_code == 201
    assert resp.json()["ticket_id"] == "t-emergency-001"


async def test_emergency_wo_publishes_wo_assigned(ac, mock_nc):
    """POST /work-orders/emergency → WO.ASSIGNED が publish される。"""
    m._nc = mock_nc
    resp = await ac.post("/work-orders/emergency", json=EMERGENCY_BODY)
    assert resp.status_code == 201
    mock_nc.publish.assert_awaited_once()
    subject = mock_nc.publish.call_args[0][0]
    assert subject == WO.ASSIGNED


async def test_complete_emergency_sets_completed(ac, mock_nc):
    """PATCH /work-orders/{id}/complete-emergency → 200、Completed かつ done_at 設定。"""
    m._nc = mock_nc
    create_resp = await ac.post("/work-orders/emergency", json=EMERGENCY_BODY)
    wo_id = create_resp.json()["work_order_id"]
    mock_nc.publish.reset_mock()

    resp = await ac.patch(f"/work-orders/{wo_id}/complete-emergency")
    assert resp.status_code == 200
    data = resp.json()
    assert data["work_order_status"] == "Completed"
    assert data["done_at"] is not None


async def test_complete_emergency_publishes_event(ac, mock_nc):
    """PATCH /complete-emergency → WO.EMERGENCY_COMPLETED が publish される。"""
    m._nc = mock_nc
    create_resp = await ac.post("/work-orders/emergency", json=EMERGENCY_BODY)
    wo_id = create_resp.json()["work_order_id"]
    mock_nc.publish.reset_mock()

    await ac.patch(f"/work-orders/{wo_id}/complete-emergency")
    mock_nc.publish.assert_awaited_once()
    subject = mock_nc.publish.call_args[0][0]
    assert subject == WO.EMERGENCY_COMPLETED


async def test_complete_emergency_not_found(ac, mock_nc):
    """存在しない wo_id に PATCH → 404。"""
    m._nc = mock_nc
    resp = await ac.patch("/work-orders/nonexistent-id/complete-emergency")
    assert resp.status_code == 404


async def test_complete_emergency_type_mismatch(ac):
    """通常 WO の wo_id に PATCH → 409。"""
    create_resp = await ac.post("/work-orders", json={
        "ticket_id": "t-001",
        "title": "通常WO",
        "work_order_type": "CorrectiveMaintenance",
    })
    assert create_resp.status_code == 201
    wo_id = create_resp.json()["work_order_id"]

    resp = await ac.patch(f"/work-orders/{wo_id}/complete-emergency")
    assert resp.status_code == 409
