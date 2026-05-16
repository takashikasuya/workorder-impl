"""
Payment スキーマ
OWL: gutp:Payment (core.ttl)

OWL備考:
  gutp:appliesTo の range が rec:Agent になっているのは ontology のバグ。
  コメント「当該支払いが対象とするワークオーダー」に従い work_order_id: str として実装する。
  gutp:currncy は OWL 上のタイポ → currency として正規化。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class PaymentStatus(StrEnum):
    PENDING = "Pending"
    PAID = "Paid"
    CANCELLED = "Cancelled"


class PaymentCreate(BaseModel):
    """gutp:Payment 生成リクエスト。

    applies_to_work_order_id: gutp:appliesTo — 対象 WorkOrder ID（必須）
    paid_to:                  gutp:paidTo — 支払先 rec:Agent ID（必須）
    currency:                 gutp:currncy (OWL typo) — ISO 4217
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    applies_to_work_order_id: str = Field(description="gutp:appliesTo — WorkOrder ID（必須）")
    paid_to: str = Field(description="gutp:paidTo — rec:Agent ID（必須）")
    payment_amount: Decimal = Field(description="gutp:paymentAmount（必須）")
    currency: str = Field(default="JPY", description="gutp:currncy (OWL typo) — ISO 4217")
    paid_at: datetime = Field(default_factory=datetime.utcnow, description="gutp:paidAt")


class Payment(PaymentCreate):
    """永続化済み Payment。"""
    payment_id: str = Field(description="gutp:paymentID")
    payment_status: PaymentStatus = Field(PaymentStatus.PENDING, description="gutp:paymentStatus")
