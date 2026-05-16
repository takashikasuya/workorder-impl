"""
CS-WO-SCHEDULER — 予防保全スケジューラー (FUN-SCHEDULE-001, FUN-SCHEDULE-002)

SOI-WOM 所属（ADR-004）。定期バッチで予防保全スケジュールを評価し、
条件成立時に StandardIssue → 定型Ticket → WorkOrder を自動発行する。
スケジュール CRUD（FUN-SCHEDULE-002 / IF-SCHEDULE-001）も担う。

依存: IF-ISSUE-001 (issue-manager), IF-TICKET-001 (ticket-manager),
      IF-WO-001 (wo-manager), IF-BUILDING-002 (building-registry)
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime

import httpx

ISSUE_MANAGER_URL = os.getenv("ISSUE_MANAGER_URL", "http://issue-manager:8000")
TICKET_MANAGER_URL = os.getenv("TICKET_MANAGER_URL", "http://ticket-manager:8000")
WO_MANAGER_URL = os.getenv("WO_MANAGER_URL", "http://wo-manager:8000")
SCHEDULE_INTERVAL_SEC = int(os.getenv("SCHEDULE_INTERVAL_SEC", "300"))


async def run_cycle(client: httpx.AsyncClient) -> None:
    """1スケジュールサイクルを実行する (FUN-SCHEDULE-001)。

    TODO: スケジュール定義を DB/設定ファイルから読み込む。
    """
    now = datetime.utcnow()
    # ダミー実装: 実際はスケジュール定義を評価してトリガー条件を確認する
    print(f"[wo-scheduler] cycle at {now.isoformat()}")


async def main() -> None:
    async with httpx.AsyncClient() as client:
        while True:
            await run_cycle(client)
            await asyncio.sleep(SCHEDULE_INTERVAL_SEC)


if __name__ == "__main__":
    asyncio.run(main())
