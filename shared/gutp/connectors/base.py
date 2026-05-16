"""
コネクタ抽象基盤 — ビルOS からの観測データ受信プロトコルを抽象化する。

新しいプロトコル（gRPC, MQTT, etc.）を追加する場合:
  1. `Connector` Protocol を実装するクラスを作成する
  2. gutp/connectors/{protocol}/ ディレクトリに配置する
  3. obs_collector/main.py で ConnectorRegistry.register() を呼ぶ

現在の実装:
  - gutp/connectors/rest/  : HTTP Webhook（ビルOS → POST /ingest/iot-event 等）
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable, Protocol


@dataclass
class IngressEvent:
    """プロトコル非依存の正規化済み受信イベント。

    Connector 実装はプロトコル固有の受信データをこの形式に変換して
    on_event コールバックに渡す。
    """
    event_type: str          # "IoTEvent" | "Report"
    payload: dict[str, Any]  # IoTEventCreate / ReportCreate と同じキー構造
    source_protocol: str     # "rest" | "grpc" | "mqtt" ...
    received_at: datetime = field(default_factory=datetime.utcnow)


OnEventCallback = Callable[[IngressEvent], Awaitable[None]]


class Connector(Protocol):
    """ビルOS コネクタ プロトコル。

    全てのコネクタはこのプロトコルに準拠すること。
    FastAPI ルーターを返す場合は `as_router()` を実装する（REST 向け）。
    長期稼働プロセスの場合は `start()` / `stop()` を実装する。
    """
    name: str

    async def start(self) -> None:
        """コネクタを起動する（ポーリング・gRPC サーバ等）。"""
        ...

    async def stop(self) -> None:
        """コネクタを停止する。"""
        ...


class ConnectorRegistry:
    """登録されたコネクタを管理し、ライフサイクルを制御する。"""

    def __init__(self) -> None:
        self._connectors: list[Connector] = []

    def register(self, connector: Connector) -> None:
        self._connectors.append(connector)

    async def start_all(self) -> None:
        await asyncio.gather(*(c.start() for c in self._connectors))

    async def stop_all(self) -> None:
        await asyncio.gather(*(c.stop() for c in self._connectors))
