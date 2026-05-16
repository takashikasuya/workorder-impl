"""
WorkOrder / ServiceTask / Booking スキーマ
OWL: gutp:WorkOrder, gutp:ServiceTask, gutp:Booking (core.ttl)

workorder_type: gutp:WorkOrderTypeScheme の SKOS Concept に準拠。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class WorkOrderStatus(StrEnum):
    OPEN = "Open"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"


class BookingStatus(StrEnum):
    TENTATIVE = "Tentative"
    CONFIRMED = "Confirmed"
    CANCELLED = "Cancelled"


# ── ServiceTask ───────────────────────────────────────────────────────────────

class ServiceTaskCreate(BaseModel):
    """gutp:ServiceTask 生成リクエスト。

    precedes_task_ids: gutp:precedes — このタスクが先行する後続タスク ID リスト。
    performed_at:      gutp:performedAt — 実施場所 (rec:Space IRI/ID)
    performed_on:      gutp:performedOn — 対象設備 (rec:Asset IRI/ID)
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(description="gutp:title（必須）")
    description: str | None = Field(None, description="gutp:description")
    precedes_task_ids: list[str] = Field(
        default_factory=list,
        description="gutp:precedes — このタスクより後に実行すべきタスク ID",
    )
    performed_at: str | None = Field(None, description="gutp:performedAt — rec:Space ID")
    performed_on: str | None = Field(None, description="gutp:performedOn — rec:Asset ID")


class ServiceTask(ServiceTaskCreate):
    """永続化済み ServiceTask。

    OWL備考: taskID の xsd:dateTime 型指定は ontology のタイポ。実装では str を使用。
    """
    task_id: str = Field(description="gutp:taskID — システム払出 UUID")
    work_order_id: str = Field(description="gutp:isServiceTaskOf — 属する WorkOrder ID")
    is_completed: bool = Field(False)
    completed_at: datetime | None = None


# ── Booking ───────────────────────────────────────────────────────────────────

class BookingCreate(BaseModel):
    """gutp:Booking 生成リクエスト。

    assigned_to:  gutp:assignedTo — 担当者 (rec:Agent ID, 必須)
    assigned_at:  gutp:assignedAt — 予約場所 (rec:Space ID, 省略可)
    assigned_on:  gutp:assignedOn — 予約設備 (rec:Asset ID, 省略可)
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    work_order_id: str = Field(description="gutp:forWorkOrder — 対象 WorkOrder ID")
    assigned_to: str = Field(description="gutp:assignedTo — rec:Agent ID（必須）")
    assigned_at: str | None = Field(None, description="gutp:assignedAt — rec:Space ID")
    assigned_on: str | None = Field(None, description="gutp:assignedOn — rec:Asset ID")
    scheduled_start: datetime = Field(description="gutp:scheduledStart（必須）")
    scheduled_end: datetime = Field(description="gutp:scheduledEnd（必須）")


class Booking(BookingCreate):
    """永続化済み Booking。"""
    booking_id: str = Field(description="gutp:bookingID")
    booking_status: BookingStatus = Field(BookingStatus.TENTATIVE, description="gutp:bookingStatus")


# ── WorkOrder ─────────────────────────────────────────────────────────────────

class WorkOrderCreate(BaseModel):
    """gutp:WorkOrder 生成リクエスト。

    work_order_type: gutp:WorkOrderTypeScheme の SKOS Concept prefLabel
                     例: "PreventiveMaintenance", "CorrectiveMaintenance", "Inspection"
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    ticket_id: str = Field(description="gutp:isWorkOrderOf — 属する Ticket ID")
    title: str = Field(description="gutp:title（必須）")
    work_order_type: str = Field(
        description="gutp:workOrderType — SKOS Concept（例: 'CorrectiveMaintenance'）"
    )
    description: str | None = Field(None, description="gutp:description")
    tasks: list[ServiceTaskCreate] = Field(
        default_factory=list,
        description="gutp:hasServiceTask — 初期 ServiceTask リスト（min 1）",
    )


class EmergencyWorkOrderCreate(BaseModel):
    """緊急 WO 生成リクエスト（FUN-WO-007）。Ticket 承認フローをバイパスして即時発行する。"""
    model_config = ConfigDict(str_strip_whitespace=True)

    reason: str = Field(description="緊急理由（必須）")
    ticket_id: str | None = Field(None, description="関連 Ticket ID（任意）")
    tasks: list[ServiceTaskCreate] = Field(default_factory=list)


class WorkOrder(BaseModel):
    """永続化済み WorkOrder。"""
    model_config = ConfigDict(str_strip_whitespace=True)

    work_order_id: str = Field(description="gutp:workOrderID")
    ticket_id: str | None = Field(None, description="gutp:isWorkOrderOf")
    title: str
    work_order_type: str = Field(description="gutp:workOrderType")
    work_order_status: WorkOrderStatus = Field(WorkOrderStatus.OPEN, description="gutp:workOrderStatus")
    description: str | None = None
    task_ids: list[str] = Field(default_factory=list)
    estimated_cost: Decimal | None = Field(None, description="gutp:estimatedCost")
    actual_cost: Decimal | None = Field(None, description="gutp:actualCost")
    started_at: datetime | None = Field(None, description="gutp:startedAt")
    done_at: datetime | None = Field(None, description="gutp:doneAt")
    created_at: datetime = Field(default_factory=datetime.utcnow)
