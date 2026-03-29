from __future__ import annotations

import httpx

from agent_ludens.models import PeerRecord, RequestAccepted, RequestCreate


class PeerClient:
    async def send_request(self, peer: PeerRecord, payload: RequestCreate) -> RequestAccepted:
        headers = {"X-Agent-Token": peer.token} if peer.token else {}
        async with httpx.AsyncClient(base_url=peer.base_url, timeout=30.0) as client:
            response = await client.post("/v1/requests", json=payload.model_dump(mode="json"), headers=headers)
            response.raise_for_status()
            return RequestAccepted.model_validate(response.json())
