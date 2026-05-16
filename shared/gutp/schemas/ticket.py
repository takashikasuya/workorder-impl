"""
Ticket / Estimate スキーマ
OWL: gutp:Ticket, gutp:Estimate (core.ttl)

gutp:currncy は OWL 上のタイポ。本スキーマでは currency として正規化する。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EstimateStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class TicketStatus(StrEnum):
    OPEN = "Open"
    IN_PROGRESS = "InProgress"
    PENDING_ESTIMATE = "PendingEstimate"
    PENDING_APPROVAL = "PendingApproval"
    CLOSED = "Closed"


# ── Estimate ──────────────────────────────────────────────────────────────────

class EstimateCreate(BaseModel):
    """gutp:Estimate 生成リクエスト。

    estimated_duration: gutp:estimatedDuration (xsd:duration) → ISO 8601 文字列（例: "P2D", "PT8H"）
    currency:           gutp:currncy (OWL typo) — ISO 4217 通貨コード（例: "JPY"）
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    ticket_id: str = Field(description="紐づく Ticket ID")
    title: str = Field(description="gutp:title（必須）")
    estimated_cost: Decimal = Field(description="gutp:estimatedCost（必須）")
    estimated_duration: str = Field(description="gutp:estimatedDuration — ISO 8601 期間（例: 'P2D'）")
    currency: str = Field(default="JPY", description="gutp:currncy（OWL typo） — ISO 4217")
    description: str | None = Field(None, description="gutp:description")


class Estimate(EstimateCreate):
    """永続化済み Estimate。"""
    estimate_id: str = Field(description="gutp:estimateID")
    estimate_status: EstimateStatus = Field(EstimateStatus.DRAFT, description="gutp:estimateStatus")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: datetime | None = None


# ── Ticket ────────────────────────────────────────────────────────────────────

class TicketCreate(BaseModel):
    """gutp:Ticket 生成リクエスト。

    addresses_issue_ids: gutp:addressesIssue（0以上） — Issue なし定型Ticket を許容。
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(description="gutp:title（必須）")
    addresses_issue_ids: list[str] = Field(
        default_factory=list,
        description="gutp:addressesIssue — 対応 Issue ID リスト（定型Ticketは空リスト可）",
    )
    priority: int = Field(default=50, description="gutp:ticketPriority — 数値（小=高優先）")
    due_at: datetime | None = Field(None, description="gutp:dueAt — 対応目標期限")
    budget: Decimal | None = Field(None, description="gutp:budget — 予算上限")
    currency: str = Field(default="JPY", description="gutp:currncy（OWL typo）")
    description: str | None = Field(None, description="gutp:description")


class Ticket(TicketCreate):
    """永続化済み Ticket。"""
    ticket_id: str = Field(description="gutp:ticketID")
    ticket_status: TicketStatus = Field(TicketStatus.OPEN, description="gutp:ticketStatus")
    estimated_cost: Decimal | None = Field(None, description="gutp:estimatedCost（承認後集計）")
    actual_cost: Decimal | None = Field(None, description="gutp:actualCost（完了後集計）")
    created_at: datetime = Field(default_factory=datetime.utcnow)
