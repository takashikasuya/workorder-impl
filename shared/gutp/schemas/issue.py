"""
Issue 階層スキーマ
OWL: gutp:Issue, gutp:StandardIssue, gutp:NonStandardIssue (core.ttl)

IssueType は gutp:IssueTypeScheme の SKOS Concept に準拠する。
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class IssueType(StrEnum):
    """gutp:issueType に対応する SKOS Concept の prefLabel 列挙。"""
    FACILITY_ASSET = "FacilityAsset"       # 設備資産
    IT_INFRASTRUCTURE = "ITInfrastructure"  # ITインフラ
    EHS = "EHS"                             # 環境・健康・安全
    SPACE_DESIGN = "SpaceDesign"           # スペース設計
    OPERATIONS = "Operations"              # オペレーション管理
    OFFICE_SERVICES = "OfficeServices"     # オフィスサービス


class IssueCreate(BaseModel):
    """Issue 生成リクエスト（gutp:Issue）。

    derived_from_id: gutp:derivedFrom — 起点 ObservationObject の ID。
                     予防保全起源の StandardIssue では None を許容する。
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(description="gutp:title（必須）")
    issue_type: IssueType = Field(description="gutp:issueType SKOS Concept（必須）")
    derived_from_id: str | None = Field(
        None,
        description="gutp:derivedFrom — IoTEvent.iot_event_id または Report.report_id（定型Issueは None 可）",
    )
    derived_from_type: Literal["IoTEvent", "Report"] | None = Field(None)
    description: str | None = Field(None, description="gutp:description")
    detected_at: datetime = Field(default_factory=datetime.utcnow, description="gutp:detectedAt")
    is_standard: bool = Field(True, description="True=StandardIssue / False=NonStandardIssue")


class Issue(IssueCreate):
    """永続化済み Issue。"""
    issue_id: str = Field(description="gutp:issueID — システム払出 UUID")


class StandardIssue(Issue):
    """gutp:StandardIssue — FM定型業務・SLA条件から生成。"""
    is_standard: Literal[True] = True


class NonStandardIssue(Issue):
    """gutp:NonStandardIssue — トレンド分析・複合異常から生成。"""
    is_standard: Literal[False] = False
