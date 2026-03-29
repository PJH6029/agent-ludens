from __future__ import annotations

from agent_ludens.config import AgentSettings
from agent_ludens.models import (
    ActivityRecord,
    ActivityStatus,
    Namespace,
    QueueItem,
    QueueSnapshot,
    RequestSource,
    RequestStatus,
)
from agent_ludens.prompting import build_prompt_header


def test_prompt_header_contains_contract_sections() -> None:
    settings = AgentSettings(enable_supervisor=False)
    activity = ActivityRecord(
        activity_id="act_123",
        kind="human_task",
        namespace=Namespace.MAIN_TASK,
        status=ActivityStatus.PENDING,
        request_ids=["req_123"],
        session_id="session-1",
        folder_path="/tmp/act_123",
        summary_path="/tmp/act_123/summary.md",
        checkpoint_path="/tmp/act_123/checkpoint.json",
        created_at="2026-03-29T00:00:00Z",
        updated_at="2026-03-29T00:00:00Z",
    )
    queue = QueueSnapshot(
        queued_count=1,
        leased_count=0,
        items=[
            QueueItem(
                request_id="req_123",
                kind="human_task",
                priority=50,
                status=RequestStatus.QUEUED,
                created_at="2026-03-29T00:00:00Z",
                source=RequestSource(type="human", id="cli"),
            )
        ],
    )
    checkpoint = {
        "objective": "Do the task",
        "completed_steps": ["Started planning."],
        "pending_steps": ["Run Codex."],
        "known_constraints": ["Use durable state."],
    }
    header = build_prompt_header(settings, queue, activity, checkpoint)
    assert "Agent identity:" in header
    assert "Queue snapshot:" in header
    assert "Pending next steps:" in header
    assert "Durable state files:" in header
