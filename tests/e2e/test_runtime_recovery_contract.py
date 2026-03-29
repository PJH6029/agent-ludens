from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from agent_ludens.adapters import CodexAdapter
from agent_ludens.app import create_app
from agent_ludens.config import AgentSettings
from agent_ludens.models import CodexTurnResult
from agent_ludens.supervisor import AgentRuntime
from tests.helpers import wait_for_request_completion


class RecoverThenResumeAdapter(CodexAdapter):
    def __init__(self) -> None:
        self.calls: list[str | None] = []

    async def run_turn(
        self,
        *,
        activity_id: str,
        prompt: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CodexTurnResult:
        self.calls.append(session_id)
        if len(self.calls) == 1:
            session_id = "resume-session-1"
            return CodexTurnResult(
                session_id=session_id,
                final_message="",
                raw_jsonl=[
                    json.dumps({"type": "thread.started", "thread_id": session_id}),
                    json.dumps({"type": "turn.started"}),
                    json.dumps({"type": "turn.failed", "error": {"message": "Temporary adapter failure"}}),
                ],
                exit_code=1,
                stderr="Temporary adapter failure",
                error_code="temporary_failure",
                recoverable=True,
            )

        assert session_id == "resume-session-1"
        return CodexTurnResult(
            session_id=session_id,
            final_message="Recovered after resume.",
            raw_jsonl=[
                json.dumps({"type": "thread.started", "thread_id": session_id}),
                json.dumps({"type": "turn.started"}),
                json.dumps({"type": "item.completed", "item": {"id": "item_0", "type": "agent_message", "text": "Recovered after resume."}}),
                json.dumps({"type": "turn.completed"}),
            ],
            exit_code=0,
        )


@pytest.mark.asyncio
async def test_recoverable_failure_reuses_persisted_session_id(settings_factory: Callable[..., AgentSettings]) -> None:
    settings = settings_factory(enable_supervisor=True, enable_free_time=False)
    adapter = RecoverThenResumeAdapter()
    runtime = AgentRuntime(settings, adapter=adapter)
    app = create_app(settings=settings, runtime=runtime)

    await runtime.start()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/v1/requests",
            json={
                "kind": "human_task",
                "priority": 50,
                "source": {"type": "human", "id": "cli"},
                "summary": "Retry with resume",
                "details": {"instructions": "Preserve the existing session on retry."},
            },
        )
        request_id = response.json()["request_id"]
        request_detail = await wait_for_request_completion(client, request_id)
        activity_detail = await client.get(f"/v1/activities/{request_detail['activity_id']}")
        events = (await client.get("/v1/events", params={"limit": 20})).json()

    await runtime.shutdown()

    assert request_detail["status"] == "completed"
    assert request_detail["result"]["session_id"] == "resume-session-1"
    assert activity_detail.status_code == 200
    assert activity_detail.json()["session_id"] == "resume-session-1"
    assert adapter.calls == [None, "resume-session-1"]
    assert any(event["type"] == "request.requeued" and event["request_id"] == request_id for event in events)
