"""
CS-BUILDING-REGISTRY — 建物構成レジストリ (FUN-BUILDING-001)

提供: IF-BUILDING-002 — 内部 REST API（Space/Device 一覧照会）
依存: IF-BUILDING-001 — ビルOS REST API（外部）

起動時および定期的にビルOS からトポロジーを取得し、内部レジストリに保存する。
CS-WO-MANAGER 等が ServiceTask の performedAt / performedOn を設定する際の
参照データ（Space・Device 一覧）を提供する。

環境変数:
  BUILDING_OS_URL           ビルOS の BaseURL (default: http://localhost:5000)
  BUILDING_OS_TOKEN         Bearer トークン (開発: 任意文字列 / 本番: Azure AD JWT)
  BUILDING_SYNC_INTERVAL_SEC 同期周期（秒, default: 300）
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from gutp.clients.building_os import BuildingOSClient

from .sync import TopologyRegistry

logging.basicConfig(level=logging.INFO)

_registry = TopologyRegistry()
_sync_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _sync_task
    client = BuildingOSClient()

    async with client:
        # 初回同期（起動時）
        try:
            await _registry.sync_once(client)
        except Exception:
            logging.getLogger(__name__).warning(
                "Initial sync failed — registry is empty. Will retry on next cycle."
            )

        # 定期同期ループをバックグラウンドで起動
        async def _loop():
            async with BuildingOSClient() as c:
                await _registry.run_sync_loop(c)

        _sync_task = asyncio.create_task(_loop())
        yield

    if _sync_task:
        _sync_task.cancel()


app = FastAPI(title="building-registry", lifespan=lifespan)


@app.get("/healthz")
async def health() -> dict:
    return {
        "status": "ok",
        "last_synced_at": _registry.last_synced_at(),
        "buildings": len(_registry.get_all_buildings()),
    }


# ── IF-BUILDING-002: 内部トポロジー照会 API ──────────────────────────────────

@app.get("/topology/buildings")
async def list_buildings() -> list[dict]:
    """登録済みビル一覧を返す。"""
    return _registry.get_all_buildings()


@app.get("/topology/buildings/{building_dt_id}/floors")
async def list_floors(building_dt_id: str) -> list[dict]:
    """指定ビルのフロア一覧を返す。"""
    result = _registry.get_floors(building_dt_id)
    if not result and not any(b["dt_id"] == building_dt_id for b in _registry.get_all_buildings()):
        raise HTTPException(404, detail="Building not found")
    return result


@app.get("/topology/spaces")
async def list_spaces(building_dt_id: str | None = None) -> list[dict]:
    """Space 一覧を返す。building_dt_id でフィルタ可能。

    ServiceTask.performed_at の候補として利用する。
    dt_id が rec:Space 参照キー（gutp:performedAt）になる。
    """
    return _registry.get_spaces(building_dt_id)


@app.get("/topology/devices")
async def list_devices(building_dt_id: str | None = None) -> list[dict]:
    """Device 一覧を返す。building_dt_id でフィルタ可能。

    ServiceTask.performed_on の候補として利用する。
    dt_id が rec:Asset 参照キー（gutp:performedOn）になる。
    """
    return _registry.get_devices(building_dt_id)


@app.post("/topology/sync", status_code=202)
async def trigger_sync() -> dict:
    """手動同期をトリガーする（管理用）。"""
    async def _do():
        async with BuildingOSClient() as c:
            await _registry.sync_once(c)

    asyncio.create_task(_do())
    return {"status": "sync triggered"}
