from __future__ import annotations

from collections.abc import Callable

import pytest
from httpx import ASGITransport, AsyncClient

from agent_ludens.adapters import FakeCodexAdapter
from agent_ludens.app import create_app
from agent_ludens.config import AgentSettings
from agent_ludens.models import RequestStatus
from agent_ludens.supervisor import AgentRuntime


@pytest.mark.asyncio
async def test_api_bootstrap_and_queue_persistence(
    settings_factory: Callable[..., AgentSettings],
) -> None:
    settings = settings_factory(enable_supervisor=False)
    runtime = AgentRuntime(settings, adapter=FakeCodexAdapter())
    app = create_app(settings=settings, runtime=runtime)
    await runtime.start()
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://testserver') as client:
        health = await client.get('/healthz')
        assert health.status_code == 200
        assert health.json()['ok'] is True

        create_response = await client.post(
            '/v1/requests',
            json={
                'kind': 'human_task',
                'priority': 50,
                'source': {'type': 'human', 'id': 'cli'},
                'summary': 'Summarize notes',
                'details': {'instructions': 'be concise'},
            },
        )
        assert create_response.status_code == 202
        request_id = create_response.json()['request_id']

        request_detail = await client.get(f'/v1/requests/{request_id}')
        assert request_detail.status_code == 200
        assert request_detail.json()['status'] == RequestStatus.QUEUED.value

        queue_snapshot = await client.get('/v1/queue')
        assert queue_snapshot.status_code == 200
        assert queue_snapshot.json()['queued_count'] == 1
    await runtime.shutdown()


@pytest.mark.asyncio
async def test_peer_registration_endpoint(
    runtime_client: tuple[AgentRuntime, AsyncClient],
) -> None:
    _, client = runtime_client
    response = await client.post(
        '/v1/peers',
        json={
            'agent_id': 'planner-7102',
            'role': 'planner',
            'base_url': 'http://127.0.0.1:7102',
            'token': None,
        },
    )
    assert response.status_code == 201
    peers = await client.get('/v1/peers')
    assert peers.status_code == 200
    assert peers.json()[0]['agent_id'] == 'planner-7102'
