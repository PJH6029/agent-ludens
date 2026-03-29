from __future__ import annotations

import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from agent_ludens.adapters import RealCodexAdapter
from agent_ludens.app import create_app
from agent_ludens.config import AgentSettings
from agent_ludens.models import (
    PeerRecord,
    ReplyTarget,
    RequestCreate,
    RequestKind,
    RequestSource,
    RequestStatus,
)
from agent_ludens.peer_client import PeerClient
from agent_ludens.supervisor import AgentRuntime
from tests.helpers import wait_for_request_completion

pytestmark = [pytest.mark.live, pytest.mark.codex_real]


def _live_enabled() -> bool:
    return os.getenv("AGENT_LUDENS_RUN_LIVE") == "1"


@pytest.mark.skipif(not _live_enabled(), reason="set AGENT_LUDENS_RUN_LIVE=1 to run live Codex tests")
@pytest.mark.asyncio
async def test_live_codex_exec_and_resume(tmp_path: Path) -> None:
    settings = AgentSettings(  # type: ignore[call-arg]
        task_memory_root=tmp_path / ".task-memory",
        workspace_root=Path.cwd(),
        adapter_mode="real",
        enable_supervisor=False,
    )
    adapter = RealCodexAdapter(settings)
    first = await adapter.run_turn(activity_id="act_live", prompt="Reply with exactly LIVE_OK.")
    assert first.exit_code == 0
    assert first.final_message == "LIVE_OK"
    assert first.session_id

    second = await adapter.run_turn(
        activity_id="act_live",
        session_id=first.session_id,
        prompt="Reply with exactly LIVE_RESUME_OK.",
    )
    assert second.exit_code == 0
    assert second.final_message == "LIVE_RESUME_OK"
    assert second.session_id == first.session_id


@pytest.mark.skipif(not _live_enabled(), reason="set AGENT_LUDENS_RUN_LIVE=1 to run live Codex tests")
@pytest.mark.asyncio
async def test_live_runtime_request_path(tmp_path: Path) -> None:
    settings = AgentSettings(  # type: ignore[call-arg]
        task_memory_root=tmp_path / ".task-memory",
        workspace_root=Path.cwd(),
        adapter_mode="real",
        enable_supervisor=True,
        enable_free_time=False,
    )
    runtime = AgentRuntime(settings, adapter=RealCodexAdapter(settings))
    app = create_app(settings=settings, runtime=runtime)
    await runtime.start()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/v1/requests",
            json={
                "kind": "human_task",
                "priority": 50,
                "source": {"type": "human", "id": "cli"},
                "summary": "Live runtime smoke test",
                "details": {"instructions": "Reply with exactly LIVE_RUNTIME_OK."},
            },
        )
        request_id = response.json()["request_id"]
        request_detail = await wait_for_request_completion(
            client,
            request_id,
            timeout_seconds=30.0,
        )
        assert request_detail["status"] == "completed"
        assert request_detail["result"]["message"] == "LIVE_RUNTIME_OK"
        assert request_detail["result"]["session_id"]
    await runtime.shutdown()


@pytest.mark.skipif(not _live_enabled(), reason="set AGENT_LUDENS_RUN_LIVE=1 to run live Codex tests")
@pytest.mark.asyncio
async def test_live_peer_request_accept_and_poll_round_trip(tmp_path: Path) -> None:
    sender_settings = AgentSettings(  # type: ignore[call-arg]
        agent_id="planner-live-7101",
        role="planner",
        port=7101,
        task_memory_root=tmp_path / ".task-memory-sender",
        workspace_root=Path.cwd(),
        adapter_mode="real",
        enable_supervisor=False,
        enable_free_time=False,
    )
    receiver_settings = AgentSettings(  # type: ignore[call-arg]
        agent_id="writer-live-7102",
        role="writer",
        port=7102,
        task_memory_root=tmp_path / ".task-memory-receiver",
        workspace_root=Path.cwd(),
        adapter_mode="real",
        enable_supervisor=True,
        enable_free_time=False,
    )

    sender_runtime = AgentRuntime(sender_settings, adapter=RealCodexAdapter(sender_settings))
    receiver_runtime = AgentRuntime(receiver_settings, adapter=RealCodexAdapter(receiver_settings))
    sender_app = create_app(settings=sender_settings, runtime=sender_runtime)
    receiver_app = create_app(settings=receiver_settings, runtime=receiver_runtime)

    await sender_runtime.start()
    await receiver_runtime.start()
    try:
        async with AsyncClient(transport=ASGITransport(app=sender_app), base_url="http://sender.test") as sender_client:
            register_response = await sender_client.post(
                "/v1/peers",
                json={
                    "agent_id": receiver_settings.agent_id,
                    "role": receiver_settings.role,
                    "base_url": "http://receiver.test",
                    "token": None,
                },
            )
            assert register_response.status_code == 201
            peers_response = await sender_client.get("/v1/peers")
            peer = PeerRecord.model_validate(peers_response.json()[0])

        peer_client = PeerClient(transport_factory=lambda: ASGITransport(app=receiver_app), timeout=60.0)
        accepted = await peer_client.send_request(
            peer,
            RequestCreate(
                kind=RequestKind.AGENT_TASK,
                priority=60,
                source=RequestSource(
                    type="agent",
                    id=sender_settings.agent_id,
                    reply_to=ReplyTarget(
                        base_url="http://sender.test",
                        request_id="req_live_origin_123",
                    ),
                ),
                summary="Live peer runtime smoke test",
                details={"instructions": "Reply with exactly LIVE_PEER_OK."},
            ),
        )
        assert accepted.status == RequestStatus.QUEUED

        request_detail = await peer_client.wait_for_completion(
            peer,
            accepted.request_id,
            timeout_seconds=60.0,
            poll_interval_seconds=0.1,
        )
        assert request_detail.status == RequestStatus.COMPLETED
        assert request_detail.source.reply_to is not None
        assert request_detail.source.reply_to.request_id == "req_live_origin_123"
        assert request_detail.result is not None
        assert request_detail.result["message"] == "LIVE_PEER_OK"
        assert request_detail.result["session_id"]
    finally:
        await receiver_runtime.shutdown()
        await sender_runtime.shutdown()
