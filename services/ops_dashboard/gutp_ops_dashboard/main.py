"""
CS-OPS-DASHBOARD — 運用管理ダッシュボード BFF (FUN-OPS-001, FUN-OPS-002, FUN-OPS-003)

提供: IF-OPS-001 — FM管理者向け集約 REST API + 静的ダッシュボード UI (/dashboard)
依存: IF-ISSUE-001 / IF-TICKET-001 / IF-WO-001 / IF-PAYMENT-001（リクエスト時に並列集約）
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections import defaultdict
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from gutp.schemas.workorder import ServiceTaskCreate

logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

app = FastAPI(title="CS-OPS-DASHBOARD", version="0.1.0")

_STATIC = Path(__file__).parent.parent / "static"
if _STATIC.exists():
    app.mount("/dashboard", StaticFiles(directory=_STATIC, html=True), name="dashboard")


async def _fetch_all() -> tuple[list, list, list, list]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        results = await asyncio.gather(
            client.get(f"{BACKEND_URL}/issues"),
            client.get(f"{BACKEND_URL}/tickets"),
            client.get(f"{BACKEND_URL}/work-orders"),
            client.get(f"{BACKEND_URL}/payments"),
            return_exceptions=True,
        )

    labels = ("/issues", "/tickets", "/work-orders", "/payments")

    def _safe(r, label: str) -> list:
        if isinstance(r, Exception):
            logger.warning("_fetch_all: %s unreachable: %s", label, r)
            return []
        if r.status_code != 200:
            logger.warning("_fetch_all: %s returned HTTP %d", label, r.status_code)
            return []
        return r.json()

    return tuple(_safe(r, svc) for r, svc in zip(results, labels))


def _build_flows(issues: list, tickets: list, work_orders: list, payments: list) -> list[dict]:
    tickets_by_issue: dict[str, list] = defaultdict(list)
    for t in tickets:
        for iid in t.get("addresses_issue_ids", []):
            tickets_by_issue[iid].append(t)

    wos_by_ticket: dict[str, list] = defaultdict(list)
    for wo in work_orders:
        if wo.get("ticket_id"):
            wos_by_ticket[wo["ticket_id"]].append(wo)

    payments_by_wo: dict[str, list] = defaultdict(list)
    for p in payments:
        payments_by_wo[p["applies_to_work_order_id"]].append(p)

    flows = []
    for issue in issues:
        flags: set[str] = set()
        if issue.get("issue_status") == "PendingReview":
            flags.add("pending_review")

        issue_tickets = tickets_by_issue.get(issue["issue_id"], [])
        issue_wos = [wo for t in issue_tickets for wo in wos_by_ticket.get(t["ticket_id"], [])]
        issue_payments = [p for wo in issue_wos for p in payments_by_wo.get(wo["work_order_id"], [])]

        for wo in issue_wos:
            if wo.get("work_order_status") == "Completed":
                paid = any(
                    p.get("payment_status") == "Paid"
                    for p in payments_by_wo.get(wo["work_order_id"], [])
                )
                if not paid:
                    flags.add("unpaid")

        flows.append({
            "flow_id": issue["issue_id"],
            "issue": issue,
            "tickets": issue_tickets,
            "work_orders": issue_wos,
            "payments": issue_payments,
            "problem_flags": sorted(flags),
        })
    return flows


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ops/flows")
async def list_flows(
    status: str = "all",
    flow_type: str | None = Query(None, alias="type"),
) -> dict:
    """FUN-OPS-001 — Issue→Ticket→WO→Payment チェーンを並列集約して返す。"""
    issues, tickets, wos, payments = await _fetch_all()
    flows = _build_flows(issues, tickets, wos, payments)
    return {"flows": flows, "filter": {"status": status, "type": flow_type}}


@app.get("/ops/flows/{flow_id}")
async def get_flow(flow_id: str) -> dict:
    """FUN-OPS-001 — 単一フローのチェーン状態。"""
    issues, tickets, wos, payments = await _fetch_all()
    flows = _build_flows(issues, tickets, wos, payments)
    flow = next((f for f in flows if f["flow_id"] == flow_id), None)
    if not flow:
        raise HTTPException(404, detail="Flow not found")
    return flow


@app.get("/ops/flows/{flow_id}/timeline")
async def get_flow_timeline(flow_id: str) -> dict:
    """FUN-OPS-002 — フロー状態遷移ログ（監査証跡）。"""
    return {"flowId": flow_id, "timeline": []}


@app.get("/ops/problems")
async def list_problems() -> dict:
    """FUN-OPS-001 — problem_flags が非空のフローのみ返す。"""
    issues, tickets, wos, payments = await _fetch_all()
    flows = _build_flows(issues, tickets, wos, payments)
    return {"problems": [f for f in flows if f["problem_flags"]]}


@app.get("/ops/work-orders")
async def list_work_orders_proxy() -> list:
    """WO 一覧を wo-manager から転送する（タスク登録 UI 向け）。"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{BACKEND_URL}/work-orders")
    except httpx.RequestError as exc:
        raise HTTPException(502, detail=f"wo-manager への接続に失敗しました: {exc}")
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, detail=resp.text)
    return resp.json()


@app.post("/ops/work-orders/{wo_id}/tasks", status_code=201)
async def add_task_proxy(wo_id: str, body: ServiceTaskCreate) -> dict:
    """タスク追加を wo-manager へ転送する（タスク登録 UI 向け）。"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{BACKEND_URL}/work-orders/{wo_id}/tasks",
                content=body.model_dump_json(),
                headers={"Content-Type": "application/json"},
            )
    except httpx.RequestError as exc:
        raise HTTPException(502, detail=f"wo-manager への接続に失敗しました: {exc}")
    if resp.status_code not in (200, 201):
        raise HTTPException(resp.status_code, detail=resp.text)
    return resp.json()


@app.get("/ops/tickets/{ticket_id}/estimates")
async def list_ticket_estimates_proxy(ticket_id: str) -> list:
    """Ticket に紐づく Estimate 一覧を backend から取得する。"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{BACKEND_URL}/tickets/{ticket_id}/estimates")
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, detail=resp.text)
    return resp.json()


@app.post("/ops/actions")
async def post_action(action: dict) -> dict:
    """FUN-OPS-003 — 管理操作を対応 CS の API へ転送する。"""
    target_type = action.get("targetType")
    target_id = action.get("targetId")
    act = action.get("action")
    payload = action.get("payload", {})

    if target_type == "issue":
        url = f"{BACKEND_URL}/issues/{target_id}/{act}"
        method = "patch"
    elif target_type == "workorder":
        url = f"{BACKEND_URL}/work-orders/{target_id}/{act}"
        method = "patch"
    elif target_type == "ticket":
        url = f"{BACKEND_URL}/tickets/{target_id}/{act}"
        method = "patch"
    elif target_type == "estimate":
        url = f"{BACKEND_URL}/estimates/{target_id}/{act}"
        method = "patch"
    elif target_type == "report":
        url = f"{BACKEND_URL}/reports/{target_id}/{act}"
        method = "post"
    elif target_type == "ticket_create":
        url = f"{BACKEND_URL}/tickets"
        method = "post"
    elif target_type == "estimate_create":
        url = f"{BACKEND_URL}/estimates"
        method = "post"
    else:
        raise HTTPException(400, detail=f"Unknown targetType: {target_type}")

    async with httpx.AsyncClient() as client:
        resp = await (client.patch(url, json=payload) if method == "patch"
                      else client.post(url, json=payload))

    if resp.status_code not in (200, 201, 204):
        raise HTTPException(resp.status_code, detail=resp.text)
    result = resp.json() if resp.content and resp.status_code != 204 else {}
    return {"accepted": True, "forwardedTo": url, "result": result}
