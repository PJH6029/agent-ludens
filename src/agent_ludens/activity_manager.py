from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from agent_ludens.config import AgentSettings
from agent_ludens.models import (
    ActivityFiles,
    ActivityRecord,
    ActivityStatus,
    CheckpointData,
    Namespace,
)
from agent_ludens.utils import new_activity_id, utc_now_iso


class ActivityManager:
    def __init__(self, settings: AgentSettings) -> None:
        self.settings = settings
        self.root = settings.task_memory_root.resolve()
        self.ensure_layout()

    def ensure_layout(self) -> None:
        for path in (
            self.root,
            self.root / "runtime",
            self.root / "main-task",
            self.root / "preparation",
            self.root / "community",
            self.root / "maintenance",
            self.root / "peers",
            self.root / "codex",
        ):
            path.mkdir(parents=True, exist_ok=True)
        if not self.settings.session_map_path.exists():
            self.settings.session_map_path.write_text(
                json.dumps({"activities": {}}, indent=2),
                encoding="utf-8",
            )

    def activity_files(self, namespace: Namespace, activity_id: str) -> ActivityFiles:
        folder = (self.root / namespace.value / activity_id).resolve()
        folder.mkdir(parents=True, exist_ok=True)
        artifacts = folder / "artifacts"
        logs = folder / "logs"
        artifacts.mkdir(exist_ok=True)
        logs.mkdir(exist_ok=True)
        return ActivityFiles(
            folder_path=str(folder),
            state_path=str(folder / "state.json"),
            summary_path=str(folder / "summary.md"),
            checkpoint_path=str(folder / "checkpoint.json"),
            inbox_path=str(folder / "inbox.md"),
            artifacts_path=str(artifacts),
            logs_path=str(logs),
        )

    def create_activity(
        self,
        *,
        kind: str,
        namespace: Namespace,
        request_ids: list[str],
        objective: str,
        current_plan: list[str],
        pending_steps: list[str],
        activity_id: str | None = None,
        session_id: str | None = None,
    ) -> ActivityRecord:
        activity_id = activity_id or new_activity_id()
        files = self.activity_files(namespace, activity_id)
        now = utc_now_iso()
        activity = ActivityRecord(
            activity_id=activity_id,
            kind=kind,
            namespace=namespace,
            status=ActivityStatus.PENDING,
            request_ids=request_ids,
            session_id=session_id,
            folder_path=files.folder_path,
            summary_path=files.summary_path,
            checkpoint_path=files.checkpoint_path,
            checkpoint_version=1,
            created_at=now,
            updated_at=now,
        )
        self.write_state(activity)
        self.write_summary(
            activity,
            objective=objective,
            why="This activity exists because the scheduler selected it for execution.",
            completed_steps=["Activity scaffold created."],
            pending_steps=pending_steps,
            next_step=pending_steps[0] if pending_steps else "Run the next Codex turn.",
        )
        self.write_checkpoint(
            activity,
            CheckpointData(
                objective=objective,
                current_plan=current_plan,
                completed_steps=["Activity scaffold created."],
                pending_steps=pending_steps,
                important_files=[files.state_path, files.summary_path, files.checkpoint_path],
                known_constraints=[
                    "Filesystem state under .task-memory/ is canonical.",
                    "Only one active Codex-driven activity may run at a time.",
                ],
                next_prompt_seed=pending_steps[0] if pending_steps else "Run the next turn.",
            ),
        )
        Path(files.inbox_path).write_text("# Inbox\n\n", encoding="utf-8")
        return activity

    def write_state(self, activity: ActivityRecord) -> None:
        state_path = Path(activity.folder_path) / "state.json"
        state = activity.model_dump(mode="json")
        state["request_ids"] = activity.request_ids
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def write_summary(
        self,
        activity: ActivityRecord,
        *,
        objective: str,
        why: str,
        completed_steps: list[str],
        pending_steps: list[str],
        next_step: str,
    ) -> None:
        body = "\n".join(
            [
                f"# Activity {activity.activity_id}",
                "",
                "## What this activity is",
                objective,
                "",
                "## Why it exists",
                why,
                "",
                "## What is done",
                *[f"- {step}" for step in completed_steps],
                "",
                "## What remains",
                *([f"- {step}" for step in pending_steps] or ["- Nothing queued."]),
                "",
                "## What the next turn should do",
                f"- {next_step}",
                "",
            ]
        )
        Path(activity.summary_path).write_text(body, encoding="utf-8")

    def write_checkpoint(self, activity: ActivityRecord, checkpoint: CheckpointData) -> None:
        Path(activity.checkpoint_path).write_text(
            json.dumps(
                {
                    "objective": checkpoint.objective,
                    "current_plan": checkpoint.current_plan,
                    "completed_steps": checkpoint.completed_steps,
                    "pending_steps": checkpoint.pending_steps,
                    "important_files": checkpoint.important_files,
                    "known_constraints": checkpoint.known_constraints,
                    "next_prompt_seed": checkpoint.next_prompt_seed,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def read_checkpoint(self, activity: ActivityRecord) -> dict[str, Any]:
        data = json.loads(Path(activity.checkpoint_path).read_text(encoding="utf-8"))
        return cast(dict[str, Any], data)

    def append_inbox(self, activity: ActivityRecord, note: str) -> None:
        with Path(activity.folder_path, "inbox.md").open("a", encoding="utf-8") as handle:
            handle.write(f"- {utc_now_iso()} {note}\n")

    def persist_codex_artifacts(
        self,
        activity: ActivityRecord,
        *,
        raw_jsonl: list[str],
        final_message: str,
        stderr: str,
        exit_code: int,
    ) -> dict[str, str]:
        codex_dir = self.root / "codex" / activity.activity_id
        codex_dir.mkdir(parents=True, exist_ok=True)
        latest_path = codex_dir / "latest.jsonl"
        last_message_path = codex_dir / "last_message.txt"
        stderr_path = codex_dir / "stderr.log"
        metadata_path = codex_dir / "metadata.json"
        latest_path.write_text("\n".join(raw_jsonl) + ("\n" if raw_jsonl else ""), encoding="utf-8")
        last_message_path.write_text(final_message, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        metadata_path.write_text(
            json.dumps({"exit_code": exit_code, "updated_at": utc_now_iso()}, indent=2),
            encoding="utf-8",
        )
        return {
            "latest_jsonl": str(latest_path),
            "last_message": str(last_message_path),
            "stderr": str(stderr_path),
            "metadata": str(metadata_path),
        }

    def update_session_map(self, activity_id: str, session_id: str) -> None:
        data = json.loads(self.settings.session_map_path.read_text(encoding="utf-8"))
        data.setdefault("activities", {})[activity_id] = {
            "session_id": session_id,
            "last_used_at": utc_now_iso(),
        }
        self.settings.session_map_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def write_runtime_state(
        self,
        *,
        agent_state: dict[str, Any],
        scheduler_state: dict[str, Any],
    ) -> None:
        (self.root / "runtime" / "agent_state.json").write_text(
            json.dumps(agent_state, indent=2),
            encoding="utf-8",
        )
        (self.root / "runtime" / "scheduler_state.json").write_text(
            json.dumps(scheduler_state, indent=2),
            encoding="utf-8",
        )

    def log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        with (self.root / "runtime" / "event-log.jsonl").open("a", encoding="utf-8") as handle:
            event = {"type": event_type, "timestamp": utc_now_iso(), **payload}
            handle.write(json.dumps(event) + "\n")
