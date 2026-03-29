from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Sequence
from datetime import timedelta
from pathlib import Path
from typing import Any

from agent_ludens.models import (
    ActivityRecord,
    ActivityStatus,
    ErrorInfo,
    PeerRecord,
    QueueItem,
    QueueSnapshot,
    RequestAccepted,
    RequestCreate,
    RequestKind,
    RequestRecord,
    RequestSource,
    RequestStatus,
)
from agent_ludens.utils import new_request_id, payload_fingerprint, utc_now, utc_now_iso


class ConflictError(RuntimeError):
    pass


class SQLiteStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS requests (
                    request_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    source_json TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    reply_json TEXT,
                    deadline TEXT,
                    namespace_hint TEXT,
                    activity_id TEXT,
                    lease_owner TEXT,
                    leased_until TEXT,
                    idempotency_key TEXT UNIQUE,
                    payload_fingerprint TEXT,
                    result_json TEXT,
                    error_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS requests_status_priority_idx ON requests (status, priority DESC, created_at ASC);

                CREATE TABLE IF NOT EXISTS request_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS activities (
                    activity_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    namespace TEXT NOT NULL,
                    status TEXT NOT NULL,
                    session_id TEXT,
                    folder_path TEXT NOT NULL,
                    summary_path TEXT NOT NULL,
                    checkpoint_path TEXT NOT NULL,
                    checkpoint_version INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS activity_requests (
                    activity_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    PRIMARY KEY (activity_id, request_id)
                );

                CREATE TABLE IF NOT EXISTS peers (
                    agent_id TEXT PRIMARY KEY,
                    role TEXT NOT NULL,
                    base_url TEXT NOT NULL,
                    token TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.commit()

    def insert_request(self, payload: RequestCreate) -> RequestAccepted:
        with self._lock, self._connect() as conn:
            now = utc_now_iso()
            serialized = payload.model_dump(mode="json")
            fingerprint = payload_fingerprint(serialized)
            if payload.idempotency_key:
                existing = conn.execute(
                    "SELECT request_id, payload_fingerprint FROM requests WHERE idempotency_key = ?",
                    (payload.idempotency_key,),
                ).fetchone()
                if existing:
                    if existing["payload_fingerprint"] != fingerprint:
                        raise ConflictError("idempotency key reuse with different payload")
                    record = self.get_request(existing["request_id"])
                    assert record is not None
                    return RequestAccepted(
                        request_id=record.request_id,
                        status=record.status,
                        accepted_at=record.created_at,
                    )

            request_id = new_request_id()
            conn.execute(
                """
                INSERT INTO requests (
                    request_id, status, kind, priority, source_json, summary, details_json,
                    reply_json, deadline, namespace_hint, activity_id, lease_owner, leased_until,
                    idempotency_key, payload_fingerprint, result_json, error_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    RequestStatus.QUEUED,
                    payload.kind,
                    payload.priority,
                    json.dumps(payload.source.model_dump(mode="json")),
                    payload.summary,
                    json.dumps(payload.details),
                    json.dumps(payload.reply.model_dump(mode="json")) if payload.reply else None,
                    payload.deadline,
                    payload.namespace_hint,
                    payload.activity_id,
                    None,
                    None,
                    payload.idempotency_key,
                    fingerprint,
                    None,
                    None,
                    now,
                    now,
                ),
            )
            self._insert_request_event(conn, request_id, "enqueued", {"status": RequestStatus.QUEUED})
            conn.commit()
            return RequestAccepted(request_id=request_id, status=RequestStatus.QUEUED, accepted_at=now)

    def _insert_request_event(
        self,
        conn: sqlite3.Connection,
        request_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        conn.execute(
            "INSERT INTO request_events (request_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?)",
            (request_id, event_type, json.dumps(payload or {}), utc_now_iso()),
        )

    def _row_to_request(self, row: sqlite3.Row | None) -> RequestRecord | None:
        if row is None:
            return None
        return RequestRecord(
            request_id=row["request_id"],
            status=RequestStatus(row["status"]),
            kind=RequestKind(row["kind"]),
            priority=row["priority"],
            source=RequestSource.model_validate_json(row["source_json"]),
            summary=row["summary"],
            details=json.loads(row["details_json"]),
            reply=None if row["reply_json"] is None else json.loads(row["reply_json"]),
            deadline=row["deadline"],
            namespace_hint=row["namespace_hint"],
            activity_id=row["activity_id"],
            lease_owner=row["lease_owner"],
            leased_until=row["leased_until"],
            idempotency_key=row["idempotency_key"],
            result=None if row["result_json"] is None else json.loads(row["result_json"]),
            error=None if row["error_json"] is None else ErrorInfo.model_validate_json(row["error_json"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_request(self, request_id: str) -> RequestRecord | None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM requests WHERE request_id = ?", (request_id,)).fetchone()
            return self._row_to_request(row)

    def list_requests_by_status(self, statuses: Sequence[RequestStatus]) -> list[RequestRecord]:
        if not statuses:
            return []
        placeholders = ",".join("?" for _ in statuses)
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM requests WHERE status IN ({placeholders}) ORDER BY created_at ASC",
                tuple(status.value for status in statuses),
            ).fetchall()
            return [record for row in rows if (record := self._row_to_request(row)) is not None]

    def lease_next_request(self, lease_owner: str, lease_ttl_seconds: int) -> RequestRecord | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM requests WHERE status = ? ORDER BY priority DESC, created_at ASC LIMIT 1",
                (RequestStatus.QUEUED,),
            ).fetchone()
            if row is None:
                return None

            lease_deadline = utc_now() + timedelta(seconds=max(lease_ttl_seconds, 0))
            leased_until = lease_deadline.isoformat().replace("+00:00", "Z")
            conn.execute(
                "UPDATE requests SET status = ?, lease_owner = ?, leased_until = ?, updated_at = ? WHERE request_id = ?",
                (RequestStatus.LEASED, lease_owner, leased_until, utc_now_iso(), row["request_id"]),
            )
            self._insert_request_event(
                conn,
                row["request_id"],
                "leased",
                {"lease_owner": lease_owner, "lease_ttl_seconds": lease_ttl_seconds},
            )
            conn.commit()
            return self.get_request(row["request_id"])

    def reclaim_expired_leases(self, now: str | None = None) -> list[str]:
        reference_time = now or utc_now_iso()
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT request_id, lease_owner, leased_until
                FROM requests
                WHERE status = ? AND leased_until IS NOT NULL AND leased_until <= ?
                ORDER BY leased_until ASC
                """,
                (RequestStatus.LEASED, reference_time),
            ).fetchall()
            reclaimed_ids: list[str] = []
            for row in rows:
                conn.execute(
                    "UPDATE requests SET status = ?, lease_owner = NULL, leased_until = NULL, updated_at = ? WHERE request_id = ?",
                    (RequestStatus.QUEUED, utc_now_iso(), row["request_id"]),
                )
                self._insert_request_event(
                    conn,
                    row["request_id"],
                    "lease_reclaimed",
                    {
                        "expired_at": row["leased_until"],
                        "previous_lease_owner": row["lease_owner"],
                    },
                )
                reclaimed_ids.append(row["request_id"])
            conn.commit()
            return reclaimed_ids

    def mark_request_running(self, request_id: str, activity_id: str) -> RequestRecord:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE requests SET status = ?, activity_id = ?, updated_at = ? WHERE request_id = ?",
                (RequestStatus.RUNNING, activity_id, utc_now_iso(), request_id),
            )
            self._insert_request_event(conn, request_id, "running", {"activity_id": activity_id})
            conn.commit()
        record = self.get_request(request_id)
        assert record is not None
        return record

    def requeue_request(self, request_id: str, activity_id: str | None = None) -> RequestRecord:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE requests SET status = ?, activity_id = COALESCE(?, activity_id), lease_owner = NULL, leased_until = NULL, updated_at = ? WHERE request_id = ?",
                (RequestStatus.QUEUED, activity_id, utc_now_iso(), request_id),
            )
            self._insert_request_event(conn, request_id, "requeued", {"activity_id": activity_id})
            conn.commit()
        record = self.get_request(request_id)
        assert record is not None
        return record

    def cancel_request(self, request_id: str) -> RequestRecord | None:
        record = self.get_request(request_id)
        if record is None:
            return None
        target_status = (
            RequestStatus.CANCELLED
            if record.status == RequestStatus.QUEUED
            else RequestStatus.CANCELLATION_REQUESTED
        )
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE requests SET status = ?, updated_at = ? WHERE request_id = ?",
                (target_status, utc_now_iso(), request_id),
            )
            self._insert_request_event(conn, request_id, "cancelled", {"status": target_status})
            conn.commit()
        return self.get_request(request_id)

    def finalize_cancelled_request(self, request_id: str) -> RequestRecord:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE requests SET status = ?, lease_owner = NULL, leased_until = NULL, updated_at = ? WHERE request_id = ?",
                (RequestStatus.CANCELLED, utc_now_iso(), request_id),
            )
            self._insert_request_event(conn, request_id, "cancelled_terminal")
            conn.commit()
        record = self.get_request(request_id)
        assert record is not None
        return record

    def complete_request(self, request_id: str, result: dict[str, Any]) -> RequestRecord:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE requests SET status = ?, lease_owner = NULL, leased_until = NULL, result_json = ?, updated_at = ? WHERE request_id = ?",
                (RequestStatus.COMPLETED, json.dumps(result), utc_now_iso(), request_id),
            )
            self._insert_request_event(conn, request_id, "completed", result)
            conn.commit()
        record = self.get_request(request_id)
        assert record is not None
        return record

    def fail_request(self, request_id: str, error: ErrorInfo) -> RequestRecord:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE requests SET status = ?, lease_owner = NULL, leased_until = NULL, error_json = ?, updated_at = ? WHERE request_id = ?",
                (RequestStatus.FAILED, error.model_dump_json(), utc_now_iso(), request_id),
            )
            self._insert_request_event(conn, request_id, "failed", error.model_dump(mode="json"))
            conn.commit()
        record = self.get_request(request_id)
        assert record is not None
        return record

    def get_queue_snapshot(self, limit: int = 50) -> QueueSnapshot:
        with self._lock, self._connect() as conn:
            queued_count = conn.execute(
                "SELECT COUNT(*) FROM requests WHERE status = ?",
                (RequestStatus.QUEUED,),
            ).fetchone()[0]
            leased_count = conn.execute(
                "SELECT COUNT(*) FROM requests WHERE status = ?",
                (RequestStatus.LEASED,),
            ).fetchone()[0]
            rows = conn.execute(
                """
                SELECT * FROM requests
                WHERE status IN (?, ?, ?, ?)
                ORDER BY priority DESC, created_at ASC
                LIMIT ?
                """,
                (
                    RequestStatus.QUEUED,
                    RequestStatus.LEASED,
                    RequestStatus.RUNNING,
                    RequestStatus.CANCELLATION_REQUESTED,
                    limit,
                ),
            ).fetchall()
            items = [
                QueueItem(
                    request_id=row["request_id"],
                    kind=RequestKind(row["kind"]),
                    priority=row["priority"],
                    status=RequestStatus(row["status"]),
                    created_at=row["created_at"],
                    source=RequestSource.model_validate_json(row["source_json"]),
                )
                for row in rows
            ]
            return QueueSnapshot(queued_count=queued_count, leased_count=leased_count, items=items)

    def get_queue_depth(self) -> int:
        return self.get_queue_snapshot(limit=1).queued_count

    def create_activity(self, activity: ActivityRecord) -> ActivityRecord:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO activities (
                    activity_id, kind, namespace, status, session_id, folder_path, summary_path,
                    checkpoint_path, checkpoint_version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    activity.activity_id,
                    activity.kind,
                    activity.namespace,
                    activity.status,
                    activity.session_id,
                    activity.folder_path,
                    activity.summary_path,
                    activity.checkpoint_path,
                    activity.checkpoint_version,
                    activity.created_at,
                    activity.updated_at,
                ),
            )
            for request_id in activity.request_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO activity_requests (activity_id, request_id) VALUES (?, ?)",
                    (activity.activity_id, request_id),
                )
            conn.commit()
        stored = self.get_activity(activity.activity_id)
        assert stored is not None
        return stored

    def update_activity(
        self,
        activity_id: str,
        *,
        status: ActivityStatus | None = None,
        session_id: str | None = None,
    ) -> ActivityRecord:
        current = self.get_activity(activity_id)
        assert current is not None
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE activities SET status = ?, session_id = ?, updated_at = ? WHERE activity_id = ?",
                (
                    status or current.status,
                    session_id if session_id is not None else current.session_id,
                    utc_now_iso(),
                    activity_id,
                ),
            )
            conn.commit()
        updated = self.get_activity(activity_id)
        assert updated is not None
        return updated

    def get_activity(self, activity_id: str) -> ActivityRecord | None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM activities WHERE activity_id = ?", (activity_id,)).fetchone()
            if row is None:
                return None
            request_ids = [
                r[0]
                for r in conn.execute(
                    "SELECT request_id FROM activity_requests WHERE activity_id = ? ORDER BY request_id ASC",
                    (activity_id,),
                ).fetchall()
            ]
            return ActivityRecord(
                activity_id=row["activity_id"],
                kind=row["kind"],
                namespace=row["namespace"],
                status=row["status"],
                session_id=row["session_id"],
                folder_path=row["folder_path"],
                summary_path=row["summary_path"],
                checkpoint_path=row["checkpoint_path"],
                checkpoint_version=row["checkpoint_version"],
                request_ids=request_ids,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def list_activities(
        self,
        *,
        status: ActivityStatus | None = None,
        namespace: str | None = None,
        limit: int = 50,
    ) -> list[ActivityRecord]:
        query = "SELECT activity_id FROM activities WHERE 1=1"
        params: list[Any] = []
        if status is not None:
            query += " AND status = ?"
            params.append(status.value)
        if namespace is not None:
            query += " AND namespace = ?"
            params.append(namespace)
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        with self._lock, self._connect() as conn:
            activity_ids = [row[0] for row in conn.execute(query, params).fetchall()]
        return [activity for activity_id in activity_ids if (activity := self.get_activity(activity_id)) is not None]

    def bind_activity_request(self, activity_id: str, request_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO activity_requests (activity_id, request_id) VALUES (?, ?)",
                (activity_id, request_id),
            )
            conn.execute(
                "UPDATE requests SET activity_id = ?, updated_at = ? WHERE request_id = ?",
                (activity_id, utc_now_iso(), request_id),
            )
            conn.commit()

    def upsert_peer(self, peer: PeerRecord) -> PeerRecord:
        now = utc_now_iso()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO peers (agent_id, role, base_url, token, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET role = excluded.role, base_url = excluded.base_url,
                    token = excluded.token, updated_at = excluded.updated_at
                """,
                (peer.agent_id, peer.role, peer.base_url, peer.token, now, now),
            )
            conn.commit()
        stored = self.get_peer(peer.agent_id)
        assert stored is not None
        return stored

    def get_peer(self, agent_id: str) -> PeerRecord | None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM peers WHERE agent_id = ?", (agent_id,)).fetchone()
            if row is None:
                return None
            return PeerRecord(
                agent_id=row["agent_id"],
                role=row["role"],
                base_url=row["base_url"],
                token=row["token"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def list_peers(self) -> list[PeerRecord]:
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT * FROM peers ORDER BY agent_id ASC").fetchall()
            return [
                PeerRecord(
                    agent_id=row["agent_id"],
                    role=row["role"],
                    base_url=row["base_url"],
                    token=row["token"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]
