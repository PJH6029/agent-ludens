from __future__ import annotations

import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from agent_ludens.adapters import RealCodexAdapter
from agent_ludens.app import create_app
from agent_ludens.config import AgentSettings
from agent_ludens.supervisor import AgentRuntime
from tests.helpers import wait_for_request_completion

pytestmark = [pytest.mark.live, pytest.mark.codex_real]


def _live_enabled() -> bool:
    return os.getenv("AGENT_LUDENS_RUN_LIVE") == "1"


@pytest.mark.skipif(not _live_enabled(), reason="set AGENT_LUDENS_RUN_LIVE=1 to run live Codex tests")
@pytest.mark.asyncio
async def test_live_codex_exec_and_resume(tmp_path: Path) -> None:
    settings = AgentSettings(
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
    settings = AgentSettings(
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
