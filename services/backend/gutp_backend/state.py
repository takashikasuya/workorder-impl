"""Shared in-memory stores and TopologyRegistry for all backend modules."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime

import nats
from gutp.clients.building_os import BuildingOSClient
from gutp.schemas.building import BuildingTopology, DeviceNode, SpaceNode
from gutp.schemas.issue import Issue
from gutp.schemas.observation import IoTEvent, Report
from gutp.schemas.payment import Payment
from gutp.schemas.ticket import Estimate, Ticket
from gutp.schemas.workorder import Booking, ServiceTask, WorkOrder

logger = logging.getLogger(__name__)

SYNC_INTERVAL_SEC = int(os.getenv("BUILDING_SYNC_INTERVAL_SEC", "300"))


class TopologyRegistry:
    def __init__(self) -> None:
        self._topologies: dict[str, BuildingTopology] = {}
        self._last_synced_at: datetime | None = None

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

    async def sync_once(self, client: BuildingOSClient) -> None:
        buildings = await client.get_buildings()
        logger.info("sync: %d buildings found", len(buildings))
        for building in buildings:
            try:
                floors = await client.get_floors(building.dt_id)
                device_details = await client.get_device_details(building.dt_id)
                spaces_raw = await client.get_spaces()
                spaces = [
                    SpaceNode(
                        dt_id=s.dt_id, id=s.id, name=s.name,
                        building_dt_id=building.dt_id, building_name=building.name,
                    )
                    for s in spaces_raw
                ]
                devices = [
                    DeviceNode(
                        dt_id=dd.device.dt_id, id=dd.device.id, name=dd.device.name,
                        device_type=dd.device.device_type,
                        space_dt_id=dd.space.dt_id if dd.space else None,
                        floor_dt_id=dd.floor.dt_id if dd.floor else None,
                        building_dt_id=building.dt_id,
                        space_name=dd.space.name if dd.space else None,
                        floor_name=dd.floor.name if dd.floor else None,
                        building_name=building.name,
                    )
                    for dd in device_details
                ]
                self._topologies[building.dt_id] = BuildingTopology(
                    building=building, floors=floors, spaces=spaces, devices=devices,
                )
                logger.info("sync: building=%s floors=%d spaces=%d devices=%d",
                            building.name, len(floors), len(spaces), len(devices))
            except Exception:
                logger.exception("sync failed for building %s", building.dt_id)
        self._last_synced_at = datetime.utcnow()

    async def run_sync_loop(self, client: BuildingOSClient) -> None:
        while True:
            try:
                await self.sync_once(client)
            except Exception:
                logger.exception("sync cycle error")
            await asyncio.sleep(SYNC_INTERVAL_SEC)


# ── Shared stores ────────────────────────────────────────────────────────────
nc: nats.aio.client.Client | None = None
topology: TopologyRegistry = TopologyRegistry()

iot_events: dict[str, IoTEvent] = {}
reports: dict[str, Report] = {}
pending_reports: dict[str, tuple[Report, datetime]] = {}

schedules: dict = {}
issues: dict[str, Issue] = {}
tickets: dict[str, Ticket] = {}
estimates: dict[str, Estimate] = {}
work_orders: dict[str, WorkOrder] = {}
service_tasks: dict[str, ServiceTask] = {}
bookings: dict[str, Booking] = {}
payments: dict[str, Payment] = {}
