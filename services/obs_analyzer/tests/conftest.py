from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import gutp_obs_analyzer.main as m
import pytest
from gutp.schemas.observation import Report


@pytest.fixture(autouse=True)
def clear_state():
    m._pending_reports.clear()
    yield
    m._pending_reports.clear()


@pytest.fixture
def mock_nc():
    nc = AsyncMock()
    nc.publish = AsyncMock()
    return nc


@pytest.fixture
def sample_report():
    return Report(report_id="r-001", title="Test", report_comment="test comment")


@pytest.fixture
def old_report(sample_report):
    """ESCALATION_THRESHOLD_SEC を超えた受信時刻を持つ pending エントリ。"""
    age = timedelta(seconds=m.ESCALATION_THRESHOLD_SEC + 1)
    m._pending_reports[sample_report.report_id] = (sample_report, datetime.utcnow() - age)
    return sample_report
