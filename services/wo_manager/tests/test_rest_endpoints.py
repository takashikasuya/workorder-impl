"""FUN-WO-002/003/004/005/006: wo-manager REST エンドポイントのユニットテスト。"""

from __future__ import annotations

WO_BODY = {
    "ticket_id": "t-001",
    "title": "空調修理",
    "work_order_type": "CorrectiveMaintenance",
    "description": "空調設備の交換",
    "tasks": [
        {"title": "部品調達", "description": None},
        {"title": "現地作業", "description": None},
    ],
}

BOOKING_BODY = {
    "work_order_id": "wo-placeholder",
    "assigned_to": "worker-1",
    "scheduled_start": "2024-06-01T09:00:00",
    "scheduled_end": "2024-06-01T17:00:00",
}


async def test_create_work_order(ac):
    resp = await ac.post("/work-orders", json=WO_BODY)
    assert resp.status_code == 201
    data = resp.json()
    assert "work_order_id" in data
    assert data["title"] == "空調修理"
    assert data["work_order_status"] == "Open"
    assert len(data["task_ids"]) == 2


async def test_get_work_order(ac):
    create_resp = await ac.post("/work-orders", json=WO_BODY)
    wo_id = create_resp.json()["work_order_id"]

    resp = await ac.get(f"/work-orders/{wo_id}")
    assert resp.status_code == 200
    assert resp.json()["work_order_id"] == wo_id


async def test_get_work_order_not_found(ac):
    resp = await ac.get("/work-orders/nonexistent-id")
    assert resp.status_code == 404


async def test_complete_task_updates_status(ac):
    create_resp = await ac.post("/work-orders", json=WO_BODY)
    data = create_resp.json()
    wo_id = data["work_order_id"]
    task_id = data["task_ids"][0]

    resp = await ac.patch(f"/work-orders/{wo_id}/tasks/{task_id}/complete")
    assert resp.status_code == 200
    # WO はまだ OPEN（他のタスクが残っている）
    assert resp.json()["work_order_status"] == "Open"


async def test_all_tasks_complete_closes_wo(ac):
    body = {**WO_BODY, "tasks": [{"title": "唯一のタスク", "description": None}]}
    create_resp = await ac.post("/work-orders", json=body)
    data = create_resp.json()
    wo_id = data["work_order_id"]
    task_id = data["task_ids"][0]

    resp = await ac.patch(f"/work-orders/{wo_id}/tasks/{task_id}/complete")
    assert resp.status_code == 200
    assert resp.json()["work_order_status"] == "Completed"


async def test_create_booking(ac):
    create_resp = await ac.post("/work-orders", json={**WO_BODY, "tasks": []})
    wo_id = create_resp.json()["work_order_id"]

    booking_body = {**BOOKING_BODY, "work_order_id": wo_id}
    resp = await ac.post("/bookings", json=booking_body)
    assert resp.status_code == 201
    assert "booking_id" in resp.json()
