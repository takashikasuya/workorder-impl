"""
NATS サブジェクト定数 — interfaces.yaml の async-pub-sub IF に対応。

IF-OBS-003   obs.iot-event.created / obs.report.created / obs.report.evaluated
             （CS-OBS-COLLECTOR が publish）
IF-ISSUE-002 issue.created / issue.updated / issue.resolved
IF-TICKET-002 ticket.estimate.approved / ticket.status.updated
IF-WO-002    wo.assigned / wo.emergency.completed
             （CS-WO-MANAGER が publish、CS-NOTIFY-DISPATCHER が購読・ADR-003）
IF-NOTIFY-001 obs.report.escalation
             （CS-OBS-ANALYZER が publish、CS-NOTIFY-DISPATCHER が購読）
             ※ OBS クラスに定義されているが所属IFは IF-NOTIFY-001（IF-OBS-003 ではない）
"""


class OBS:
    IOT_EVENT_CREATED = "obs.iot-event.created"
    REPORT_CREATED = "obs.report.created"
    # IF-OBS-003: CS-OBS-COLLECTOR が publish（FM評価操作の結果 approve/reject）、CS-OBS-ANALYZER が購読
    REPORT_EVALUATED = "obs.report.evaluated"
    # IF-NOTIFY-001 (not IF-OBS-003): CS-OBS-ANALYZER が publish、CS-NOTIFY-DISPATCHER が購読
    REPORT_ESCALATION = "obs.report.escalation"


class ISSUE:
    CREATED = "issue.created"
    UPDATED = "issue.updated"
    RESOLVED = "issue.resolved"


class TICKET:
    ESTIMATE_APPROVED = "ticket.estimate.approved"
    STATUS_UPDATED = "ticket.status.updated"


class WO:
    """IF-WO-002 — CS-WO-MANAGER が publish、CS-NOTIFY-DISPATCHER が購読（ADR-003）。"""

    ASSIGNED = "wo.assigned"
    EMERGENCY_COMPLETED = "wo.emergency.completed"
