from __future__ import annotations

import json

import pytest

from agent_ludens.adapters import FakeCodexAdapter
from agent_ludens.supervisor import AgentRuntime
from tests.helpers import wait_for_request_completion


@pytest.mark.asyncio
async def test_runtime_events_endpoint_surfaces_recent_request_events(runtime_client) -> None:
    runtime, client = runtime_client
    response = await client.post(
        "/v1/requests",
        json={
            "kind": "human_task",
            "priority": 50,
            "source": {"type": "human", "id": "cli"},
            "summary": "Surface runtime events",
            "details": {"instructions": "Produce observable artifacts."},
        },
    )
    request_id = response.json()["request_id"]
    request_detail = await wait_for_request_completion(client, request_id)

    events_response = await client.get("/v1/events", params={"limit": 20})
    assert events_response.status_code == 200
    events = events_response.json()

    assert any(event["type"] == "request.leased" and event["request_id"] == request_id for event in events)
    completed_event = next(event for event in events if event["type"] == "request.completed" and event["request_id"] == request_id)
    assert completed_event["activity_id"] == request_detail["activity_id"]
    assert completed_event["session_id"] == request_detail["result"]["session_id"]

    event_log_path = runtime.settings.runtime_dir / "event-log.jsonl"
    assert event_log_path.exists()
    persisted_events = [json.loads(line) for line in event_log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(event["type"] == "request.completed" and event["request_id"] == request_id for event in persisted_events)


@pytest.mark.asyncio
async def test_supervisor_lock_enforces_single_runtime_per_task_memory_root(settings_factory) -> None:
    settings = settings_factory(enable_supervisor=True, enable_free_time=False)
    primary = AgentRuntime(settings, adapter=FakeCodexAdapter())
    contender = AgentRuntime(
        settings.model_copy(update={"agent_id": "planner-7102"}),
        adapter=FakeCodexAdapter(),
    )

    await primary.start()
    try:
        with pytest.raises(RuntimeError, match="supervisor lock"):
            await contender.start()
    finally:
        await primary.shutdown()

    await contender.start()
    await contender.shutdown()
