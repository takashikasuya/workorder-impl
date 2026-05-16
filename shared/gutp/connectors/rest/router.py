"""
REST コネクタ — ビルOS からの HTTP Webhook を受信する FastAPI ルーター。

ビルOS は以下のエンドポイントに POST する:
  POST /ingest/iot-event  — IoTEvent 受信 (IF-OBS-001)
  POST /ingest/report     — Report 受信  (IF-OBS-002)

受信後は IngressEvent に正規化して on_event コールバックを呼ぶ。
obs_collector/main.py がこのルーターをマウントし、on_event に NATS publish を渡す。

将来 gRPC コネクタを追加する場合は gutp/connectors/grpc/ を作成し、
同様のコールバック方式で実装する。
"""

from __future__ import annotations

from fastapi import APIRouter, status

from ...schemas.observation import IoTEventCreate, ReportCreate
from ..base import IngressEvent, OnEventCallback


def make_rest_router(on_event: OnEventCallback) -> APIRouter:
    """on_event コールバックを注入した REST コネクタ ルーターを返す。

    Args:
        on_event: 正規化済み IngressEvent を受け取る非同期コールバック。
                  obs_collector が NATS publish ロジックを渡す。
    """
    router = APIRouter(prefix="/ingest", tags=["connector:rest"])

    @router.post("/iot-event", status_code=status.HTTP_202_ACCEPTED)
    async def receive_iot_event(body: IoTEventCreate) -> dict[str, str]:
        """ビルOS からの IoTEvent を受信する (IF-OBS-001)。"""
        event = IngressEvent(
            event_type="IoTEvent",
            payload=body.model_dump(),
            source_protocol="rest",
        )
        await on_event(event)
        return {"status": "accepted"}

    @router.post("/report", status_code=status.HTTP_202_ACCEPTED)
    async def receive_report(body: ReportCreate) -> dict[str, str]:
        """ビルOS / 利用者アプリからの Report を受信する (IF-OBS-002)。"""
        event = IngressEvent(
            event_type="Report",
            payload=body.model_dump(),
            source_protocol="rest",
        )
        await on_event(event)
        return {"status": "accepted"}

    return router
