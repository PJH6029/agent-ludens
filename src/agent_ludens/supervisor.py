from __future__ import annotations

import asyncio
import json
import os
from itertools import cycle
from pathlib import Path
from typing import Any

from agent_ludens.activity_manager import ActivityManager
from agent_ludens.adapters import CodexAdapter, build_adapter
from agent_ludens.config import AgentSettings
from agent_ludens.models import (
    ActivityDetail,
    ActivityRecord,
    ActivityStatus,
    AgentInfo,
    AgentStatus,
    CheckpointData,
    ErrorInfo,
    Namespace,
    RequestKind,
    RequestRecord,
    RequestStatus,
)
from agent_ludens.prompting import (
    build_free_time_instruction,
    build_prompt_header,
    build_request_instruction,
)
from agent_ludens.store import SQLiteStore
from agent_ludens.utils import utc_now_iso


def namespace_for_request(request: RequestRecord) -> Namespace:
    if request.namespace_hint in {namespace.value for namespace in Namespace}:
        return Namespace(request.namespace_hint)
    if request.kind == RequestKind.PREPARATION_TASK:
        return Namespace.PREPARATION
    if request.kind == RequestKind.COMMUNITY_TASK:
        return Namespace.COMMUNITY
    if request.kind == RequestKind.MAINTENANCE_TASK:
        return Namespace.MAINTENANCE
    return Namespace.MAIN_TASK


class AgentRuntime:
    def __init__(
        self,
        settings: AgentSettings,
        *,
        store: SQLiteStore | None = None,
        activity_manager: ActivityManager | None = None,
        adapter: CodexAdapter | None = None,
    ) -> None:
        self.settings = settings
        self.store = store or SQLiteStore(settings.database_path)
        self.activity_manager = activity_manager or ActivityManager(settings)
        self.adapter = adapter or build_adapter(settings)
        self._status = AgentStatus.BOOT
        self._loop_task: asyncio.Task[None] | None = None
        self._wakeup = asyncio.Event()
        self._stopping = False
        self._current_request_id: str | None = None
        self._current_activity_id: str | None = None
        self._current_session_id: str | None = None
        self._current_run_task: asyncio.Task[None] | None = None
        self._supervisor_lock_held = False
        self._free_time_cycle = cycle(
            [Namespace.PREPARATION, Namespace.COMMUNITY, Namespace.MAINTENANCE]
        )

    async def start(self) -> None:
        self.activity_manager.ensure_layout()
        try:
            if self.settings.enable_supervisor:
                self._acquire_supervisor_lock()
            self._recover_state()
            await self._write_runtime_state()
            if self.settings.enable_supervisor and self._loop_task is None:
                self._stopping = False
                self._loop_task = asyncio.create_task(self._run_loop())
        except Exception:
            self._release_supervisor_lock()
            raise

    async def shutdown(self) -> None:
        self._stopping = True
        self._wakeup.set()
        if self._current_run_task is not None:
            self._current_run_task.cancel()
            try:
                await self._current_run_task
            except asyncio.CancelledError:
                pass
        if self._loop_task is not None:
            await self._loop_task
            self._loop_task = None
        self._status = AgentStatus.IDLE
        await self._write_runtime_state()
        self._release_supervisor_lock()

    def wakeup(self) -> None:
        self._wakeup.set()

    async def request_cancellation(self, request_id: str) -> None:
        if self._current_request_id == request_id and self._current_run_task is not None:
            self._current_run_task.cancel()
        self.wakeup()

    def health(self) -> dict[str, Any]:
        return {
            "ok": True,
            "agent_id": self.settings.agent_id,
            "role": self.settings.role,
            "status": self._status,
        }

    def agent_info(self) -> AgentInfo:
        return AgentInfo(
            agent_id=self.settings.agent_id,
            role=self.settings.role,
            port=self.settings.port,
            status=self._status,
            active_activity_id=self._current_activity_id,
            queue_depth=self.store.get_queue_depth(),
            current_session_id=self._current_session_id,
        )

    def list_activity_details(
        self,
        *,
        status: ActivityStatus | None = None,
        namespace: str | None = None,
        limit: int = 50,
    ) -> list[ActivityDetail]:
        activities = self.store.list_activities(status=status, namespace=namespace, limit=limit)
        return [self.get_activity_detail(activity.activity_id) for activity in activities]

    def get_activity_detail(self, activity_id: str) -> ActivityDetail:
        activity = self.store.get_activity(activity_id)
        if activity is None:
            raise KeyError(activity_id)
        summary = self._read_text(activity.summary_path)
        return ActivityDetail(
            activity_id=activity.activity_id,
            kind=activity.kind,
            namespace=activity.namespace,
            status=activity.status,
            summary=summary,
            session_id=activity.session_id,
            request_ids=activity.request_ids,
            checkpoint_version=activity.checkpoint_version,
            updated_at=activity.updated_at,
        )

    def list_recent_events(self, *, limit: int = 50) -> list[dict[str, Any]]:
        return self.activity_manager.read_recent_events(limit=limit)

    def _read_text(self, path: str) -> str:
        return Path(path).read_text(encoding="utf-8")

    def _recover_state(self) -> None:
        for request in self.store.list_requests_by_status(
            [
                RequestStatus.LEASED,
                RequestStatus.RUNNING,
                RequestStatus.CHECKPOINTING,
            ]
        ):
            self.store.requeue_request(request.request_id, request.activity_id)
        for request in self.store.list_requests_by_status([RequestStatus.CANCELLATION_REQUESTED]):
            self.store.finalize_cancelled_request(request.request_id)
        for activity in self.store.list_activities(limit=500):
            if activity.status in {ActivityStatus.ACTIVE, ActivityStatus.CHECKPOINTING}:
                self.store.update_activity(activity.activity_id, status=ActivityStatus.PENDING)
        self.activity_manager.log_event(
            "recovery.completed",
            {"queue_depth": self.store.get_queue_depth()},
        )

    async def _run_loop(self) -> None:
        while not self._stopping:
            self._reclaim_expired_leases()
            request = self.store.lease_next_request(
                self.settings.agent_id,
                self.settings.request_lease_ttl_seconds,
            )
            if request is not None:
                self.activity_manager.log_event(
                    "request.leased",
                    {
                        "request_id": request.request_id,
                        "lease_owner": request.lease_owner,
                        "leased_until": request.leased_until,
                    },
                )
                self._current_request_id = request.request_id
                self._status = AgentStatus.HANDLING_REQUEST
                self._current_run_task = asyncio.create_task(self._execute_request(request))
                try:
                    await self._current_run_task
                except asyncio.CancelledError:
                    pass
                finally:
                    self._current_run_task = None
                    self._current_request_id = None
                    self._current_activity_id = None
                    self._current_session_id = None
                    self._status = AgentStatus.IDLE
                    await self._write_runtime_state()
                continue

            if self.settings.enable_free_time:
                namespace = next(self._free_time_cycle)
                self._status = AgentStatus.FREE_TIME
                self._current_run_task = asyncio.create_task(self._execute_free_time(namespace))
                try:
                    await self._current_run_task
                except asyncio.CancelledError:
                    pass
                finally:
                    self._current_run_task = None
                    self._current_activity_id = None
                    self._current_session_id = None
                    self._status = AgentStatus.IDLE
                    await self._write_runtime_state()
                await self._sleep_until_wakeup()
                continue

            self._status = AgentStatus.IDLE
            await self._write_runtime_state()
            await self._sleep_until_wakeup()

    async def _sleep_until_wakeup(self) -> None:
        self._wakeup.clear()
        try:
            await asyncio.wait_for(self._wakeup.wait(), timeout=self.settings.poll_interval_seconds)
        except TimeoutError:
            return

    async def _execute_request(self, request: RequestRecord) -> None:
        activity = self._ensure_request_activity(request)
        self._current_activity_id = activity.activity_id
        self._current_session_id = activity.session_id
        self.store.mark_request_running(request.request_id, activity.activity_id)
        self.activity_manager.log_event(
            "request.running",
            {
                "request_id": request.request_id,
                "activity_id": activity.activity_id,
                "session_id": activity.session_id,
            },
        )
        activity = self.store.update_activity(activity.activity_id, status=ActivityStatus.ACTIVE, session_id=activity.session_id)
        checkpoint = self.activity_manager.read_checkpoint(activity)
        prompt = build_prompt_header(self.settings, self.store.get_queue_snapshot(limit=5), activity, checkpoint)
        turn_prompt = f"{prompt}\n\n{build_request_instruction(request)}"
        try:
            result = await self.adapter.run_turn(
                activity_id=activity.activity_id,
                prompt=turn_prompt,
                session_id=activity.session_id,
                metadata={**request.details, "summary": request.summary},
            )
        except asyncio.CancelledError:
            await self._checkpoint_request(activity, request, cancelled=self._request_cancelled(request.request_id))
            raise

        artifact_paths = self.activity_manager.persist_codex_artifacts(
            activity,
            raw_jsonl=result.raw_jsonl,
            final_message=result.final_message,
            stderr=result.stderr,
            exit_code=result.exit_code,
        )
        if result.session_id:
            activity = self.store.update_activity(activity.activity_id, session_id=result.session_id)
            self.activity_manager.update_session_map(activity.activity_id, result.session_id)
            self._current_session_id = result.session_id

        if self._request_cancelled(request.request_id):
            self.store.finalize_cancelled_request(request.request_id)
            self.store.update_activity(activity.activity_id, status=ActivityStatus.FAILED)
            self.activity_manager.log_event(
                "request.cancelled",
                {"request_id": request.request_id, "activity_id": activity.activity_id},
            )
            self.activity_manager.write_summary(
                activity,
                objective=request.summary,
                why="The request was cancelled while the activity was running.",
                completed_steps=["Cancellation was recorded."],
                pending_steps=[],
                next_step="No further action.",
            )
            return

        if result.exit_code == 0:
            self.store.complete_request(
                request.request_id,
                {
                    "message": result.final_message,
                    "activity_id": activity.activity_id,
                    "session_id": result.session_id,
                },
            )
            self.store.update_activity(activity.activity_id, status=ActivityStatus.COMPLETED, session_id=result.session_id)
            self.activity_manager.log_event(
                "request.completed",
                {
                    "request_id": request.request_id,
                    "activity_id": activity.activity_id,
                    "session_id": result.session_id,
                    "exit_code": result.exit_code,
                },
            )
            self.activity_manager.write_summary(
                activity,
                objective=request.summary,
                why="This activity fulfilled a queued request.",
                completed_steps=["Codex turn completed successfully.", f"Final message persisted at {artifact_paths['last_message']}."],
                pending_steps=[],
                next_step="No further action required.",
            )
            self.activity_manager.write_checkpoint(
                activity,
                CheckpointData(
                    objective=request.summary,
                    current_plan=["Complete the request and persist the result."],
                    completed_steps=["Codex turn completed successfully."],
                    pending_steps=[],
                    important_files=[activity.summary_path, activity.checkpoint_path, artifact_paths["latest_jsonl"]],
                    known_constraints=["Filesystem state under .task-memory/ is canonical."],
                    next_prompt_seed="Completed.",
                ),
            )
            return

        error = ErrorInfo(
            code=result.error_code or "codex_exec_failed",
            message=result.stderr or "Codex execution failed.",
            details={"activity_id": activity.activity_id},
        )
        if result.recoverable:
            self.store.requeue_request(request.request_id, activity.activity_id)
            self.store.update_activity(activity.activity_id, status=ActivityStatus.PENDING, session_id=result.session_id)
            self.activity_manager.log_event(
                "request.requeued",
                {
                    "request_id": request.request_id,
                    "activity_id": activity.activity_id,
                    "session_id": result.session_id,
                    "reason": result.error_code or "recoverable_failure",
                },
            )
            self.activity_manager.write_summary(
                activity,
                objective=request.summary,
                why="The activity hit a recoverable adapter failure and was requeued.",
                completed_steps=["Failure was captured."],
                pending_steps=["Retry the activity."],
                next_step="Retry with the existing activity and session when the supervisor picks it again.",
            )
        else:
            self.store.fail_request(request.request_id, error)
            self.store.update_activity(activity.activity_id, status=ActivityStatus.FAILED, session_id=result.session_id)
            self.activity_manager.log_event(
                "request.failed",
                {
                    "request_id": request.request_id,
                    "activity_id": activity.activity_id,
                    "session_id": result.session_id,
                    "error_code": error.code,
                },
            )
            self.activity_manager.write_summary(
                activity,
                objective=request.summary,
                why="The activity failed during Codex execution.",
                completed_steps=["Failure was persisted for inspection."],
                pending_steps=[],
                next_step="Inspect stderr and decide whether to retry manually.",
            )

    async def _checkpoint_request(self, activity: ActivityRecord, request: RequestRecord, *, cancelled: bool) -> None:
        if cancelled:
            self.store.finalize_cancelled_request(request.request_id)
            self.store.update_activity(activity.activity_id, status=ActivityStatus.FAILED)
            return
        self.store.requeue_request(request.request_id, activity.activity_id)
        self.store.update_activity(activity.activity_id, status=ActivityStatus.PENDING)
        self.activity_manager.write_summary(
            activity,
            objective=request.summary,
            why="The runtime shut down or the request was interrupted before completion.",
            completed_steps=["Progress checkpointed before requeue."],
            pending_steps=["Resume the request from the persisted activity state."],
            next_step="Resume the request when the runtime restarts.",
        )
        self.activity_manager.write_checkpoint(
            activity,
            CheckpointData(
                objective=request.summary,
                current_plan=["Resume the request using the existing activity."],
                completed_steps=["Progress checkpointed before requeue."],
                pending_steps=["Resume the request from the persisted activity state."],
                important_files=[activity.summary_path, activity.checkpoint_path],
                known_constraints=["Filesystem state under .task-memory/ is canonical."],
                next_prompt_seed="Resume the previously interrupted request.",
            ),
        )

    async def _execute_free_time(self, namespace: Namespace) -> None:
        activity = self.activity_manager.create_activity(
            kind=f"{namespace.value}_free_time",
            namespace=namespace,
            request_ids=[],
            objective=f"Spend one free-time quantum on {namespace.value} work.",
            current_plan=["Take exactly one Codex turn and then yield back to the scheduler."],
            pending_steps=["Run one safe free-time turn."],
        )
        activity = self.store.create_activity(activity)
        self._current_activity_id = activity.activity_id
        self._current_session_id = activity.session_id
        self.store.update_activity(activity.activity_id, status=ActivityStatus.ACTIVE)
        checkpoint = self.activity_manager.read_checkpoint(activity)
        prompt = build_prompt_header(self.settings, self.store.get_queue_snapshot(limit=5), activity, checkpoint)
        turn_prompt = f"{prompt}\n\n{build_free_time_instruction(namespace.value)}"
        try:
            result = await self.adapter.run_turn(
                activity_id=activity.activity_id,
                prompt=turn_prompt,
                session_id=activity.session_id,
                metadata={
                    "mode": "free_time",
                    "namespace": namespace.value,
                    "summary": f"Free time for {namespace.value}",
                    "delay_seconds": self.settings.free_time_delay_seconds,
                },
            )
        except asyncio.CancelledError:
            self.store.update_activity(activity.activity_id, status=ActivityStatus.PENDING)
            self.activity_manager.write_summary(
                activity,
                objective=f"Spend one free-time quantum on {namespace.value} work.",
                why="Free-time work was interrupted by shutdown or higher-priority work.",
                completed_steps=["Checkpoint created before yielding."],
                pending_steps=["Resume free-time work when the queue drains."],
                next_step="Resume free-time work later.",
            )
            raise

        self.activity_manager.persist_codex_artifacts(
            activity,
            raw_jsonl=result.raw_jsonl,
            final_message=result.final_message,
            stderr=result.stderr,
            exit_code=result.exit_code,
        )
        if result.session_id:
            self.store.update_activity(activity.activity_id, session_id=result.session_id)
            self.activity_manager.update_session_map(activity.activity_id, result.session_id)
            self._current_session_id = result.session_id
        if self.store.get_queue_depth() > 0:
            self.store.update_activity(activity.activity_id, status=ActivityStatus.PENDING, session_id=result.session_id)
            self.activity_manager.write_summary(
                activity,
                objective=f"Spend one free-time quantum on {namespace.value} work.",
                why="A real request arrived and free-time work yielded at the quantum boundary.",
                completed_steps=["One free-time quantum completed."],
                pending_steps=["Resume free-time work when the queue is empty again."],
                next_step="Yield to queued request processing.",
            )
            self.activity_manager.write_checkpoint(
                activity,
                CheckpointData(
                    objective=f"Spend one free-time quantum on {namespace.value} work.",
                    current_plan=["Resume free-time work when no requests are queued."],
                    completed_steps=["One free-time quantum completed."],
                    pending_steps=["Resume free-time work when the queue is empty again."],
                    important_files=[activity.summary_path, activity.checkpoint_path],
                    known_constraints=["Free-time work must yield when a queued request exists."],
                    next_prompt_seed="Resume free-time work safely after queued requests are finished.",
                ),
            )
        else:
            self.store.update_activity(activity.activity_id, status=ActivityStatus.COMPLETED, session_id=result.session_id)
            self.activity_manager.write_summary(
                activity,
                objective=f"Spend one free-time quantum on {namespace.value} work.",
                why="The runtime used idle time productively.",
                completed_steps=["One free-time quantum completed."],
                pending_steps=[],
                next_step="No further action required.",
            )

    def _ensure_request_activity(self, request: RequestRecord) -> ActivityRecord:
        if request.activity_id:
            existing = self.store.get_activity(request.activity_id)
            if existing is not None:
                return existing
        namespace = namespace_for_request(request)
        activity = self.activity_manager.create_activity(
            kind=request.kind.value,
            namespace=namespace,
            request_ids=[request.request_id],
            objective=request.summary,
            current_plan=["Build the prompt header from durable state.", "Run the next Codex turn.", "Persist outputs and update request status."],
            pending_steps=["Run the next Codex turn.", "Persist outputs and update request status."],
            activity_id=request.activity_id,
        )
        activity = self.store.create_activity(activity)
        self.store.bind_activity_request(activity.activity_id, request.request_id)
        return activity

    def _request_cancelled(self, request_id: str) -> bool:
        record = self.store.get_request(request_id)
        return record is not None and record.status == RequestStatus.CANCELLATION_REQUESTED

    async def _write_runtime_state(self) -> None:
        self.activity_manager.write_runtime_state(
            agent_state={
                "agent_id": self.settings.agent_id,
                "role": self.settings.role,
                "status": self._status,
                "active_activity_id": self._current_activity_id,
                "current_session_id": self._current_session_id,
                "updated_at": utc_now_iso(),
            },
            scheduler_state={
                "queue_depth": self.store.get_queue_depth(),
                "current_request_id": self._current_request_id,
                "updated_at": utc_now_iso(),
            },
        )
