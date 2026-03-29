from __future__ import annotations

import asyncio
from collections.abc import Callable

import httpx

from agent_ludens.models import (
    PeerRecord,
    RequestAccepted,
    RequestCreate,
    RequestRecord,
    RequestStatus,
)

TERMINAL_REQUEST_STATUSES = frozenset(
    {RequestStatus.COMPLETED, RequestStatus.FAILED, RequestStatus.CANCELLED}
)


class PeerClient:
    def __init__(
        self,
        *,
        transport_factory: Callable[[], httpx.AsyncBaseTransport] | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._transport_factory = transport_factory
        self._timeout = timeout

    def _build_client(self, peer: PeerRecord) -> httpx.AsyncClient:
        transport = self._transport_factory() if self._transport_factory else None
        return httpx.AsyncClient(base_url=peer.base_url, timeout=self._timeout, transport=transport)

    def _headers(self, peer: PeerRecord) -> dict[str, str]:
        return {"X-Agent-Token": peer.token} if peer.token else {}

    async def send_request(self, peer: PeerRecord, payload: RequestCreate) -> RequestAccepted:
        async with self._build_client(peer) as client:
            response = await client.post(
                "/v1/requests",
                json=payload.model_dump(mode="json"),
                headers=self._headers(peer),
            )
            response.raise_for_status()
            return RequestAccepted.model_validate(response.json())

    async def get_request(self, peer: PeerRecord, request_id: str) -> RequestRecord:
        async with self._build_client(peer) as client:
            response = await client.get(f"/v1/requests/{request_id}", headers=self._headers(peer))
            response.raise_for_status()
            return RequestRecord.model_validate(response.json())

    async def wait_for_completion(
        self,
        peer: PeerRecord,
        request_id: str,
        *,
        timeout_seconds: float = 30.0,
        poll_interval_seconds: float = 0.05,
    ) -> RequestRecord:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            request = await self.get_request(peer, request_id)
            if request.status in TERMINAL_REQUEST_STATUSES:
                return request
            await asyncio.sleep(poll_interval_seconds)
        raise TimeoutError(f"peer request {request_id} did not complete within {timeout_seconds} seconds")
