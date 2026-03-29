from __future__ import annotations

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from agent_ludens.adapters import FakeCodexAdapter
from agent_ludens.app import create_app
from agent_ludens.supervisor import AgentRuntime
from tests.helpers import wait_for_request_completion


@pytest.mark.asyncio
async def test_human_request_happy_path(runtime_client) -> None:
    runtime, client = runtime_client
    response = await client.post(
        "/v1/requests",
        json={
            "kind": "human_task",
            "priority": 50,
            "source": {"type": "human", "id": "cli"},
            "summary": "Summarize memory agent literature",
            "details": {"instructions": "Prepare a short memo."},
        },
    )
    request_id = response.json()["request_id"]
    request_detail = await wait_for_request_completion(client, request_id)
    assert request_detail["status"] == "completed"

    activity_id = request_detail["activity_id"]
    activity = await client.get(f"/v1/activities/{activity_id}")
    assert activity.status_code == 200
    assert "What this activity is" in activity.json()["summary"]

    latest = runtime.settings.task_memory_root / "codex" / activity_id / "latest.jsonl"
    assert latest.exists()


@pytest.mark.asyncio
async def test_peer_request_happy_path(runtime_client) -> None:
    _, client = runtime_client
    response = await client.post(
        "/v1/requests",
        json={
            "kind": "agent_task",
            "priority": 60,
            "source": {
                "type": "agent",
                "id": "planner-7102",
                "reply_to": {"base_url": "http://127.0.0.1:7102", "request_id": "req_origin_123"},
            },
            "summary": "Write a peer response",
            "details": {"instructions": "Return a structured acknowledgement."},
        },
    )
    request_id = response.json()["request_id"]
    request_detail = await wait_for_request_completion(client, request_id)
    assert request_detail["status"] == "completed"
    assert request_detail["source"]["type"] == "agent"


@pytest.mark.asyncio
async def test_restart_recovery_requeues_and_reuses_activity(settings_factory) -> None:
    settings = settings_factory(enable_supervisor=True, enable_free_time=False)
    runtime = AgentRuntime(settings, adapter=FakeCodexAdapter())
    app = create_app(settings=settings, runtime=runtime)
    await runtime.start()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/v1/requests",
            json={
                "kind": "human_task",
                "priority": 50,
                "source": {"type": "human", "id": "cli"},
                "summary": "Recover me",
                "details": {"instructions": "Recover after restart.", "delay_seconds": 1.0},
            },
        )
        request_id = response.json()["request_id"]
        deadline = asyncio.get_event_loop().time() + 2.0
        first_activity_id = None
        while asyncio.get_event_loop().time() < deadline:
            detail = (await client.get(f"/v1/requests/{request_id}")).json()
            if detail["status"] == "running":
                first_activity_id = detail["activity_id"]
                break
            await asyncio.sleep(0.05)
        assert first_activity_id is not None
    await runtime.shutdown()

    restarted = AgentRuntime(settings, adapter=FakeCodexAdapter())
    restarted_app = create_app(settings=settings, runtime=restarted)
    await restarted.start()
    async with AsyncClient(transport=ASGITransport(app=restarted_app), base_url="http://testserver") as client:
        request_detail = await wait_for_request_completion(
            client,
            request_id,
            timeout_seconds=5.0,
        )
        assert request_detail["status"] == "completed"
        assert request_detail["activity_id"] == first_activity_id
    await restarted.shutdown()


@pytest.mark.asyncio
async def test_free_time_preemption(settings_factory) -> None:
    settings = settings_factory(enable_supervisor=True, enable_free_time=True, free_time_delay_seconds=0.25)
    runtime = AgentRuntime(settings, adapter=FakeCodexAdapter())
    app = create_app(settings=settings, runtime=runtime)
    await runtime.start()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        deadline = asyncio.get_event_loop().time() + 2.0
        free_activity_id = None
        while asyncio.get_event_loop().time() < deadline:
            activities = (await client.get("/v1/activities")).json()
            if activities:
                free_activity_id = activities[0]["activity_id"]
                break
            await asyncio.sleep(0.05)
        assert free_activity_id is not None

        response = await client.post(
            "/v1/requests",
            json={
                "kind": "human_task",
                "priority": 90,
                "source": {"type": "human", "id": "cli"},
                "summary": "Interrupt free time",
                "details": {"instructions": "Handle this immediately."},
            },
        )
        request_id = response.json()["request_id"]
        request_detail = await wait_for_request_completion(client, request_id)
        assert request_detail["status"] == "completed"

        free_activity = await client.get(f"/v1/activities/{free_activity_id}")
        assert free_activity.status_code == 200
        assert free_activity.json()["status"] in {"pending", "completed"}
    await runtime.shutdown()


@pytest.mark.asyncio
async def test_approval_blocked_failure_is_surfaced(runtime_client) -> None:
    _, client = runtime_client
    response = await client.post(
        "/v1/requests",
        json={
            "kind": "human_task",
            "priority": 50,
            "source": {"type": "human", "id": "cli"},
            "summary": "Attempt a blocked action",
            "details": {"instructions": "Need approval.", "fake_behavior": "approval_blocked"},
        },
    )
    request_id = response.json()["request_id"]
    request_detail = await wait_for_request_completion(client, request_id)
    assert request_detail["status"] == "failed"
    assert request_detail["error"]["code"] == "approval_blocked"
