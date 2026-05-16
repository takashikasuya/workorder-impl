"""
CS-ISSUE-MANAGER — Issue 管理サービス (FUN-ISSUE-001, FUN-ISSUE-002)

提供: IF-ISSUE-001 (REST CRUD), IF-ISSUE-002 (NATS issue.created)
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager

import nats
from fastapi import FastAPI, HTTPException
from gutp.events.subjects import ISSUE
from gutp.schemas.issue import Issue, IssueCreate

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")

_nc: nats.aio.client.Client | None = None
_issues: dict[str, Issue] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _nc
    _nc = await nats.connect(NATS_URL)
    yield
    await _nc.drain()


app = FastAPI(title="issue-manager", lifespan=lifespan)


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/issues", status_code=201)
async def create_issue(body: IssueCreate) -> Issue:
    record = Issue(issue_id=str(uuid.uuid4()), **body.model_dump())
    _issues[record.issue_id] = record
    if _nc:
        await _nc.publish(ISSUE.CREATED, record.model_dump_json().encode())
    return record


@app.get("/issues/{issue_id}")
async def get_issue(issue_id: str) -> Issue:
    record = _issues.get(issue_id)
    if not record:
        raise HTTPException(404, detail="Issue not found")
    return record


@app.get("/issues")
async def list_issues() -> list[Issue]:
    return list(_issues.values())


@app.patch("/issues/{issue_id}/resolve")
async def resolve_issue(issue_id: str) -> Issue:
    record = _issues.get(issue_id)
    if not record:
        raise HTTPException(404, detail="Issue not found")
    if _nc:
        await _nc.publish(ISSUE.RESOLVED, record.model_dump_json().encode())
    return record
