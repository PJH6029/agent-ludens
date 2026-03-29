from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any, cast

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from agent_ludens.adapters import FakeCodexAdapter
from agent_ludens.app import create_app
from agent_ludens.config import AgentSettings
from agent_ludens.supervisor import AgentRuntime


@pytest.fixture
def settings_factory(tmp_path: Path) -> Callable[..., AgentSettings]:
    def factory(**overrides: Any) -> AgentSettings:
        base = AgentSettings.model_validate(
            {
                'task_memory_root': tmp_path / '.task-memory',
                'workspace_root': Path.cwd(),
                'enable_supervisor': True,
                'enable_free_time': False,
                'adapter_mode': 'fake',
                'poll_interval_seconds': 0.05,
                'free_time_delay_seconds': 0.15,
            }
        )
        return base.model_copy(update=overrides)

    return factory


@pytest_asyncio.fixture
async def runtime_client(
    settings_factory: Callable[..., AgentSettings],
) -> AsyncIterator[tuple[AgentRuntime, AsyncClient]]:
    settings = settings_factory()
    runtime = AgentRuntime(settings, adapter=FakeCodexAdapter())
    app = create_app(settings=settings, runtime=runtime)
    await runtime.start()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://testserver') as client:
        yield runtime, client
    await runtime.shutdown()


async def wait_for_request_completion(
    client: AsyncClient,
    request_id: str,
    *,
    timeout_seconds: float = 5.0,
) -> dict[str, Any]:
    deadline = asyncio.get_event_loop().time() + timeout_seconds
    while asyncio.get_event_loop().time() < deadline:
        response = await client.get(f'/v1/requests/{request_id}')
        response.raise_for_status()
        payload = cast(dict[str, Any], response.json())
        if payload['status'] in {'completed', 'failed', 'cancelled'}:
            return payload
        await asyncio.sleep(0.05)
    raise AssertionError(
        f'request {request_id} did not reach a terminal state within {timeout_seconds} seconds'
    )
