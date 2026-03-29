from __future__ import annotations

import tempfile
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from agent_ludens.models import RequestCreate, RequestSource, RequestStatus
from agent_ludens.store import ConflictError, SQLiteStore


@given(priorities=st.lists(st.integers(min_value=0, max_value=100), min_size=1, max_size=10))
def test_lease_prefers_highest_priority(priorities: list[int]) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        store = SQLiteStore(Path(temp_dir) / ".task-memory" / "requests.sqlite")
        for idx, priority in enumerate(priorities):
            store.insert_request(
                RequestCreate(
                    kind="human_task",
                    priority=priority,
                    source=RequestSource(type="human", id=f"cli-{idx}"),
                    summary=f"task-{idx}",
                    details={"index": idx},
                )
            )
        leased = store.lease_next_request("tester", 30)
        assert leased is not None
        assert leased.priority == max(priorities)


def test_idempotency_returns_original_request(tmp_path) -> None:
    store = SQLiteStore(tmp_path / ".task-memory" / "requests.sqlite")
    payload = RequestCreate(
        kind="human_task",
        priority=50,
        source=RequestSource(type="human", id="cli"),
        summary="Summarize notes",
        details={"instructions": "be concise"},
        idempotency_key="same-key",
    )
    accepted_one = store.insert_request(payload)
    accepted_two = store.insert_request(payload)
    assert accepted_one.request_id == accepted_two.request_id


def test_idempotency_conflict_raises(tmp_path) -> None:
    store = SQLiteStore(tmp_path / ".task-memory" / "requests.sqlite")
    store.insert_request(
        RequestCreate(
            kind="human_task",
            priority=50,
            source=RequestSource(type="human", id="cli"),
            summary="Task A",
            details={"instructions": "a"},
            idempotency_key="conflict-key",
        )
    )
    try:
        store.insert_request(
            RequestCreate(
                kind="human_task",
                priority=50,
                source=RequestSource(type="human", id="cli"),
                summary="Task B",
                details={"instructions": "b"},
                idempotency_key="conflict-key",
            )
        )
    except ConflictError:
        pass
    else:
        raise AssertionError("expected ConflictError")


def test_cancel_running_request_marks_cancellation_requested(tmp_path) -> None:
    store = SQLiteStore(tmp_path / ".task-memory" / "requests.sqlite")
    accepted = store.insert_request(
        RequestCreate(
            kind="human_task",
            priority=50,
            source=RequestSource(type="human", id="cli"),
            summary="Task A",
            details={"instructions": "a"},
        )
    )
    leased = store.lease_next_request("tester", 30)
    assert leased is not None
    running = store.mark_request_running(accepted.request_id, "act_test")
    assert running.status == RequestStatus.RUNNING
    cancelled = store.cancel_request(accepted.request_id)
    assert cancelled is not None
    assert cancelled.status == RequestStatus.CANCELLATION_REQUESTED
