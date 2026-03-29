from __future__ import annotations

import json
from typing import Any

from agent_ludens.config import AgentSettings
from agent_ludens.models import ActivityRecord, QueueSnapshot, RequestRecord

IMPORTANT_CONSTRAINTS = [
    "Filesystem state under .task-memory/ is canonical.",
    "Only one active Codex-driven activity may run at a time.",
    "Prefer compact summaries over raw transcript replay.",
]


def build_prompt_header(
    settings: AgentSettings,
    queue_snapshot: QueueSnapshot,
    activity: ActivityRecord,
    checkpoint: dict[str, Any],
) -> str:
    queue_lines = [
        f"- {item.request_id} | {item.status} | p={item.priority} | {item.summary if hasattr(item, 'summary') else item.kind}"
        for item in queue_snapshot.items[:5]
    ]
    if not queue_lines:
        queue_lines = ["- queue empty"]

    completed_lines = checkpoint.get("completed_steps") or ["None yet recorded."]
    pending_lines = checkpoint.get("pending_steps") or ["None recorded."]
    constraint_lines = checkpoint.get("known_constraints") or IMPORTANT_CONSTRAINTS

    return "\n".join(
        [
            f"Agent identity: {settings.agent_id}",
            f"Role: {settings.role}",
            f"Active activity: {activity.activity_id}",
            f"Namespace: {activity.namespace}",
            f"Current objective: {checkpoint.get('objective', 'No objective recorded.')}",
            "Queue snapshot:",
            *queue_lines,
            "Completed so far:",
            *[f"- {line}" for line in completed_lines],
            "Pending next steps:",
            *[f"- {line}" for line in pending_lines],
            "Important constraints:",
            *[f"- {line}" for line in constraint_lines],
            "Durable state files:",
            f"- state.json: {activity.folder_path}/state.json",
            f"- summary.md: {activity.summary_path}",
            f"- checkpoint.json: {activity.checkpoint_path}",
        ]
    )


def build_request_instruction(request: RequestRecord) -> str:
    details = json.dumps(request.details, indent=2, sort_keys=True)
    return "\n".join(
        [
            f"Request kind: {request.kind}",
            f"Summary: {request.summary}",
            "Structured details:",
            details,
            "Complete the request and provide a compact final result.",
        ]
    )


def build_free_time_instruction(namespace: str) -> str:
    return "\n".join(
        [
            f"Free-time namespace: {namespace}",
            "Spend one safe, low-priority quantum on preparation, maintenance, or community-facing work.",
            "Do not require approvals or destructive actions.",
            "End with a concise summary of what was explored or prepared.",
        ]
    )
