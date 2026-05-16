"""
CS-OPS-DASHBOARD — 運用管理ダッシュボード BFF (FUN-OPS-001, FUN-OPS-002, FUN-OPS-003)

提供: IF-OPS-001 — FM管理者向け集約 REST API
依存: IF-ISSUE-001 / IF-OBS-002 / IF-TICKET-001 / IF-WO-001 /
      IF-PAYMENT-001 / IF-BUILDING-002（各CSをリクエスト時に集約）

自身はデータを永続化しない（BFF）。各CSのAPIを呼び出して
業務フロー状態を集約し、問題フラグ付きで提示する。
管理操作は対応CSへ転送する。

NOTE: 本ファイルはアーキ同期によるスケルトン。集約・転送ロジックは未実装。
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Query

# 集約先 CS（IF-* に対応）
ISSUE_MANAGER_URL = os.getenv("ISSUE_MANAGER_URL", "http://issue-manager:8000")
OBS_COLLECTOR_URL = os.getenv("OBS_COLLECTOR_URL", "http://obs-collector:8000")
TICKET_MANAGER_URL = os.getenv("TICKET_MANAGER_URL", "http://ticket-manager:8000")
WO_MANAGER_URL = os.getenv("WO_MANAGER_URL", "http://wo-manager:8000")
PAYMENT_MANAGER_URL = os.getenv("PAYMENT_MANAGER_URL", "http://payment-manager:8000")
BUILDING_REGISTRY_URL = os.getenv("BUILDING_REGISTRY_URL", "http://building-registry:8000")

app = FastAPI(title="CS-OPS-DASHBOARD", version="0.1.0")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ops/flows")
async def list_flows(
    status: str = "all",
    flow_type: str | None = Query(None, alias="type"),
    from_date: str | None = Query(None, alias="from"),
    to: str | None = None,
) -> dict:
    """FUN-OPS-001 — 業務フロー状態の集約・提供。

    起点イベント（Report/IoTEvent）→ Payment のチェーン状態を各CSから集約し、
    問題状態（pending_review / conflicted / 滞留 / 精算未完了(緊急WO)）に
    フラグを付与して返す。
    TODO: 各CS API からの集約ロジックを実装する。
    """
    return {"flows": [], "filter": {"status": status, "type": flow_type}}


@app.get("/ops/flows/{flow_id}")
async def get_flow(flow_id: str) -> dict:
    """FUN-OPS-001 — 単一フローの起点〜現在のチェーン状態。"""
    return {"flowId": flow_id, "chain": []}


@app.get("/ops/flows/{flow_id}/timeline")
async def get_flow_timeline(flow_id: str) -> dict:
    """FUN-OPS-002 — フロー状態遷移ログ（監査証跡）。

    TODO: 各CSから状態遷移ログを収集し時系列整形する。
    """
    return {"flowId": flow_id, "timeline": []}


@app.get("/ops/problems")
async def list_problems() -> dict:
    """FUN-OPS-001 — pending_review / conflicted / 滞留 / 精算未完了 の集約キュー。"""
    return {"problems": []}


@app.post("/ops/actions")
async def post_action(action: dict) -> dict:
    """FUN-OPS-003 — 管理操作を対応CSのAPIへ転送する。

    body: { targetType, targetId, action, payload }
      targetType: issue|report|workorder|booking|ticket
    転送先: IF-ISSUE-001 / IF-OBS-002 / IF-WO-001 / IF-TICKET-001
    TODO: targetType に応じた転送ルーティングを実装する。
    """
    return {"accepted": True, "forwardedTo": None, "result": "not-implemented"}
