from __future__ import annotations

from datetime import datetime, timedelta

import gutp_obs_analyzer.main as m
from gutp.events.subjects import OBS
from gutp.schemas.observation import Report


async def test_report_created_adds_to_pending(sample_report):
    await m._handle_report_created(sample_report)
    assert sample_report.report_id in m._pending_reports


async def test_report_evaluated_removes_from_pending(sample_report):
    m._pending_reports[sample_report.report_id] = (sample_report, datetime.utcnow())
    await m._handle_report_evaluated(sample_report.report_id)
    assert sample_report.report_id not in m._pending_reports


async def test_report_evaluated_unknown_id_is_noop(sample_report):
    m._pending_reports[sample_report.report_id] = (sample_report, datetime.utcnow())
    await m._handle_report_evaluated("unknown-id")
    assert sample_report.report_id in m._pending_reports


async def test_scan_escalates_old_report(old_report, mock_nc):
    await m._scan_and_escalate(mock_nc)
    mock_nc.publish.assert_called_once_with(
        OBS.REPORT_ESCALATION, old_report.model_dump_json().encode()
    )
    assert old_report.report_id not in m._pending_reports


async def test_scan_does_not_escalate_fresh_report(sample_report, mock_nc):
    m._pending_reports[sample_report.report_id] = (sample_report, datetime.utcnow())
    await m._scan_and_escalate(mock_nc)
    mock_nc.publish.assert_not_called()
    assert sample_report.report_id in m._pending_reports


async def test_scan_escalates_only_old_among_mixed(mock_nc):
    old = Report(report_id="r-old", title="Old", report_comment="old")
    new = Report(report_id="r-new", title="New", report_comment="new")
    age = timedelta(seconds=m.ESCALATION_THRESHOLD_SEC + 1)
    m._pending_reports["r-old"] = (old, datetime.utcnow() - age)
    m._pending_reports["r-new"] = (new, datetime.utcnow())

    await m._scan_and_escalate(mock_nc)

    mock_nc.publish.assert_called_once_with(OBS.REPORT_ESCALATION, old.model_dump_json().encode())
    assert "r-old" not in m._pending_reports
    assert "r-new" in m._pending_reports


async def test_evaluated_report_not_escalated(old_report, mock_nc):
    await m._handle_report_evaluated(old_report.report_id)
    await m._scan_and_escalate(mock_nc)
    mock_nc.publish.assert_not_called()
