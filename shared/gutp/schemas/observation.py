"""
ObservationObject 階層スキーマ
OWL: gutp:ObservationObject, gutp:IoTEvent, gutp:Report (core.ttl)

gutp:IoTEvent  subClassOf  gutp:ObservationObject
gutp:Report    subClassOf  gutp:ObservationObject
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

# ── IoTEvent ──────────────────────────────────────────────────────────────────

class IoTEventCreate(BaseModel):
    """ビルOS からの IoTEvent 受信ペイロード（gutp:IoTEvent）。

    ioT_event_type: SKOS ConceptScheme gutp:IoTEventTypeScheme の Concept IRI または prefLabel。
    event_value:    gutp:eventValue (xsd:decimal, optional)
    event_state:    gutp:eventState (xsd:string, optional) — "ACTIVE"/"CLEAR" など
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    iot_event_type: str = Field(
        description="IoTEventType SKOS Concept IRI または prefLabel（例: 'gutp:SmokeAlarm'）"
    )
    event_value: Decimal | None = Field(None, description="観測値（gutp:eventValue）")
    event_state: str | None = Field(None, description="状態文字列（gutp:eventState）")
    source_id: str | None = Field(None, description="ビルOS 側デバイス識別子（省略可）")
    occurred_at: datetime = Field(default_factory=datetime.utcnow, description="発生時刻")


class IoTEvent(IoTEventCreate):
    """永続化済み IoTEvent（gutp:IoTEventID 付与済み）。"""
    iot_event_id: str = Field(description="gutp:IoTEventID — システム払出 UUID")
    received_at: datetime = Field(default_factory=datetime.utcnow)


# ── Report ────────────────────────────────────────────────────────────────────

class ReportCreate(BaseModel):
    """報告者（人）からの Report 投稿ペイロード（gutp:Report）。

    report_confidence: gutp:reportConfidence (xsd:integer) — 確信度 1〜100
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(description="gutp:title — 概要タイトル（必須）")
    report_comment: str = Field(description="gutp:reportComment — 自由記述コメント（必須）")
    report_confidence: Annotated[int, Field(ge=1, le=100)] | None = Field(
        None, description="gutp:reportConfidence — 確信度 1〜100"
    )


class Report(ReportCreate):
    """永続化済み Report。"""
    report_id: str = Field(description="gutp:reportID — システム払出 UUID")
    received_at: datetime = Field(default_factory=datetime.utcnow)
