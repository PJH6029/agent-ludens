from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agent_ludens.models import RequestCreate, RequestKind, RequestSource, RequestStatus
from agent_ludens.store import SQLiteStore
from agent_ludens.utils import utc_now_iso


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _set_leased_until(database_path: Path, request_id: str, leased_until: str) -> None:
    with sqlite3.connect(database_path) as conn:
        conn.execute(
            "UPDATE requests SET leased_until = ?, updated_at = ? WHERE request_id = ?",
            (leased_until, utc_now_iso(), request_id),
        )
        conn.commit()


def test_lease_records_ttl_and_expired_leases_can_be_reclaimed(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / ".task-memory" / "requests.sqlite")
    accepted = store.insert_request(
        RequestCreate(
            kind=RequestKind.HUMAN_TASK,
            priority=80,
            source=RequestSource(type="human", id="cli"),
            summary="Recover abandoned lease",
            details={"instructions": "Reclaim if the worker disappears."},
        )
    )

    leased = store.lease_next_request("tester", 30)
    assert leased is not None
    assert leased.request_id == accepted.request_id
    assert leased.status == RequestStatus.LEASED
    assert leased.lease_owner == "tester"
    assert leased.leased_until is not None
    assert _parse_timestamp(leased.leased_until) > _parse_timestamp(leased.updated_at)

    _set_leased_until(
        store.database_path,
        accepted.request_id,
        (datetime.now(UTC) - timedelta(seconds=5)).isoformat().replace("+00:00", "Z"),
    )

    reclaimed = store.reclaim_expired_leases()
    assert reclaimed == [accepted.request_id]

    reclaimed_record = store.get_request(accepted.request_id)
    assert reclaimed_record is not None
    assert reclaimed_record.status == RequestStatus.QUEUED
    assert reclaimed_record.lease_owner is None
    assert reclaimed_record.leased_until is None
    assert store.reclaim_expired_leases() == []

    released = store.lease_next_request("tester-2", 30)
    assert released is not None
    assert released.request_id == accepted.request_id
    assert released.lease_owner == "tester-2"
