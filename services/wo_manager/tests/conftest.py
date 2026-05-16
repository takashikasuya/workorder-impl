from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def mock_nc():
    nc = AsyncMock()
    nc.subscribe = AsyncMock()
    nc.drain = AsyncMock()
    nc.publish = AsyncMock()
    return nc


@pytest.fixture
async def ac(mock_nc):
    """NATS をモックした wo-manager の AsyncClient（lifespan 起動済み）。"""
    with patch("gutp_wo_manager.main.nats.connect", return_value=mock_nc):
        # グローバル状態をリセット
        import gutp_wo_manager.main as m

        m._work_orders.clear()
        m._tasks.clear()
        m._bookings.clear()

        from gutp_wo_manager.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
