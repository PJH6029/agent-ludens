from __future__ import annotations

import pytest

from agent_ludens.adapters import FakeCodexAdapter, parse_codex_events


@pytest.mark.asyncio
async def test_fake_adapter_can_surface_approval_blocked() -> None:
    adapter = FakeCodexAdapter()
    result = await adapter.run_turn(
        activity_id="act_123",
        prompt="Do something",
        metadata={"fake_behavior": "approval_blocked"},
    )
    assert result.exit_code == 1
    assert result.approval_blocked is True
    assert result.error_code == "approval_blocked"


def test_parse_codex_events_extracts_thread_id_and_message() -> None:
    thread_id, message = parse_codex_events(
        [
            {"type": "thread.started", "thread_id": "thread-1"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "hello"}},
            {"type": "turn.completed"},
        ]
    )
    assert thread_id == "thread-1"
    assert message == "hello"
