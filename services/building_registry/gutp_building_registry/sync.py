"""
建物トポロジー同期エンジン (FUN-BUILDING-001)

ビルOS から Building/Floor/Space/Device/Point 階層を取得し、
内部レジストリに保存する。定期的に再同期する。
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime

from gutp.clients.building_os import BuildingOSClient
from gutp.schemas.building import BuildingTopology, DeviceNode, SpaceNode

logger = logging.getLogger(__name__)

SYNC_INTERVAL_SEC = int(os.getenv("BUILDING_SYNC_INTERVAL_SEC", "300"))


class TopologyRegistry:
    """インメモリ トポロジーレジストリ。

    実運用では Redis / SQLite 等の永続化に置き換える。
    全サービスからのアクセスは IF-BUILDING-002 (REST API) 経由。
    """

    def __init__(self) -> None:
        self._topologies: dict[str, BuildingTopology] = {}  # keyed by building.dt_id
        self._last_synced_at: datetime | None = None

    # ── 参照 API ──────────────────────────────────────────────────────

    def get_all_buildings(self) -> list[dict]:
        return [
            {"dt_id": t.building.dt_id, "id": t.building.id, "name": t.building.name}
            for t in self._topologies.values()
        ]

    def get_floors(self, building_dt_id: str) -> list[dict]:
        topo = self._topologies.get(building_dt_id)
        if not topo:
            return []
        return [f.model_dump() for f in topo.floors]

    def get_spaces(self, building_dt_id: str | None = None) -> list[dict]:
        results: list[SpaceNode] = []
        for topo in self._topologies.values():
            if building_dt_id and topo.building.dt_id != building_dt_id:
                continue
            results.extend(topo.spaces)
        return [s.model_dump() for s in results]

    def get_devices(self, building_dt_id: str | None = None) -> list[dict]:
        results: list[DeviceNode] = []
        for topo in self._topologies.values():
            if building_dt_id and topo.building.dt_id != building_dt_id:
                continue
            results.extend(topo.devices)
        return [d.model_dump() for d in results]

    def last_synced_at(self) -> datetime | None:
        return self._last_synced_at

    # ── 同期 ──────────────────────────────────────────────────────────

    async def sync_once(self, client: BuildingOSClient) -> None:
        """ビルOS から最新トポロジーを取得してレジストリを更新する (UC-OBS-004-S01〜S03)。"""
        buildings = await client.get_buildings()
        logger.info("sync: %d buildings found", len(buildings))

        for building in buildings:
            try:
                floors = await client.get_floors(building.dt_id)
                device_details = await client.get_device_details(building.dt_id)
                spaces_raw = await client.get_spaces()

                # Space → ビル文脈を補完（フロア詳細は将来の拡張用）
                spaces: list[SpaceNode] = [
                    SpaceNode(
                        dt_id=s.dt_id,
                        id=s.id,
                        name=s.name,
                        building_dt_id=building.dt_id,
                        building_name=building.name,
                    )
                    for s in spaces_raw
                ]

                # DeviceDetail → DeviceNode（フロア・スペース文脈付き）
                devices: list[DeviceNode] = []
                for dd in device_details:
                    floor = dd.floor
                    space = dd.space
                    devices.append(DeviceNode(
                        dt_id=dd.device.dt_id,
                        id=dd.device.id,
                        name=dd.device.name,
                        device_type=dd.device.device_type,
                        space_dt_id=space.dt_id if space else None,
                        floor_dt_id=floor.dt_id if floor else None,
                        building_dt_id=building.dt_id,
                        space_name=space.name if space else None,
                        floor_name=floor.name if floor else None,
                        building_name=building.name,
                    ))

                self._topologies[building.dt_id] = BuildingTopology(
                    building=building,
                    floors=floors,
                    spaces=spaces,
                    devices=devices,
                )
                logger.info(
                    "sync: building=%s floors=%d spaces=%d devices=%d",
                    building.name, len(floors), len(spaces), len(devices),
                )
            except Exception:
                logger.exception("sync failed for building %s", building.dt_id)

        self._last_synced_at = datetime.utcnow()

    async def run_sync_loop(self, client: BuildingOSClient) -> None:
        """定期同期ループ (UC-OBS-004-S04)。"""
        while True:
            try:
                await self.sync_once(client)
            except Exception:
                logger.exception("sync cycle error")
            await asyncio.sleep(SYNC_INTERVAL_SEC)
