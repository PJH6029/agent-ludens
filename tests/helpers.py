from __future__ import annotations

import asyncio
from typing import Any, cast

from httpx import AsyncClient


async def wait_for_request_completion(
    client: AsyncClient,
    request_id: str,
    *,
    timeout_seconds: float = 5.0,
) -> dict[str, Any]:
    deadline = asyncio.get_event_loop().time() + timeout_seconds
    while asyncio.get_event_loop().time() < deadline:
        response = await client.get(f"/v1/requests/{request_id}")
        response.raise_for_status()
        payload = cast(dict[str, Any], response.json())
        if payload["status"] in {"completed", "failed", "cancelled"}:
            return payload
        await asyncio.sleep(0.05)
    raise AssertionError(
        f"request {request_id} did not reach a terminal state within {timeout_seconds} seconds"
    )
