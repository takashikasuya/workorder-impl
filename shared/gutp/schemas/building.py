"""
Building OS エンティティスキーマ
参照: gutp-bim/building_OS_test (docs/schema/swagger.yaml)

Building OS のデジタルツイン階層:
  Building → Floor → Space → Device → Point

DtId  : Azure Digital Twins ID ($dtId) — トポロジー参照のキー
id    : Business ID
name  : 表示名
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BuildingOSBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True)


# ── エンティティ ──────────────────────────────────────────────────────────────

class Building(BuildingOSBase):
    """GET /buildings レスポンスアイテム。"""
    dt_id: str = Field(alias="dtId", description="Azure Digital Twins ID")
    id: str = Field(description="Business ID")
    name: str = Field(description="ビル名")


class Floor(BuildingOSBase):
    """GET /floors レスポンスアイテム。"""
    dt_id: str = Field(alias="dtId")
    id: str
    name: str


class Space(BuildingOSBase):
    """GET /spaces レスポンスアイテム。"""
    dt_id: str = Field(alias="dtId")
    id: str
    name: str


class Device(BuildingOSBase):
    """GET /devices レスポンスアイテム。"""
    dt_id: str = Field(alias="dtId")
    id: str
    name: str
    building_name: str | None = Field(None, alias="buildingName")
    floor_number: int | None = Field(None, alias="floorNumber")
    owner: str | None = None
    site: str | None = None
    supplier: str | None = None
    gateway_id: str | None = Field(None, alias="gatewayId")
    device_type: str | None = Field(None, alias="deviceType")


class Point(BuildingOSBase):
    """GET /points レスポンスアイテム（センサー・制御ポイント）。"""
    dt_id: str = Field(alias="dtId")
    id: str
    name: str
    specification: str | None = None
    type: str | None = None
    writable: bool | None = None
    unit: str | None = None
    interval: float | None = None
    min_pres_value: int | None = Field(None, alias="minPresValue")
    max_pres_value: int | None = Field(None, alias="maxPresValue")


class DeviceDetail(BuildingOSBase):
    """GET /device-details レスポンスアイテム — Device + 位置コンテキスト。"""
    device: Device
    floor: Floor | None = None
    space: Space | None = None


# ── 内部レジストリ表現 ─────────────────────────────────────────────────────────

class SpaceNode(BuildingOSBase):
    """ワークオーダーシステム内部の Space ノード（フロア・ビル文脈付き）。

    ServiceTask.performed_at の候補として提供される。
    dt_id が rec:Space への参照キーになる。
    """
    dt_id: str
    id: str
    name: str
    floor_dt_id: str | None = None
    building_dt_id: str | None = None
    floor_name: str | None = None
    building_name: str | None = None


class DeviceNode(BuildingOSBase):
    """ワークオーダーシステム内部の Device ノード（位置コンテキスト付き）。

    ServiceTask.performed_on の候補として提供される。
    dt_id が rec:Asset への参照キーになる。
    """
    dt_id: str
    id: str
    name: str
    device_type: str | None = None
    space_dt_id: str | None = None
    floor_dt_id: str | None = None
    building_dt_id: str | None = None
    space_name: str | None = None
    floor_name: str | None = None
    building_name: str | None = None


class BuildingTopology(BuildingOSBase):
    """1ビルの完全なトポロジー（内部キャッシュ単位）。"""
    building: Building
    floors: list[Floor] = Field(default_factory=list)
    spaces: list[SpaceNode] = Field(default_factory=list)
    devices: list[DeviceNode] = Field(default_factory=list)
