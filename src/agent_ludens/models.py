from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentStatus(StrEnum):
    BOOT = "boot"
    IDLE = "idle"
    HANDLING_REQUEST = "handling_request"
    CHECKPOINTING = "checkpointing"
    FREE_TIME = "free_time"
    ERROR_BACKOFF = "error_backoff"


class RequestStatus(StrEnum):
    QUEUED = "queued"
    LEASED = "leased"
    RUNNING = "running"
    CHECKPOINTING = "checkpointing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    CANCELLATION_REQUESTED = "cancellation_requested"


class ActivityStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    CHECKPOINTING = "checkpointing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLATION_REQUESTED = "cancellation_requested"


class RequestKind(StrEnum):
    HUMAN_TASK = "human_task"
    AGENT_TASK = "agent_task"
    PREPARATION_TASK = "preparation_task"
    COMMUNITY_TASK = "community_task"
    MAINTENANCE_TASK = "maintenance_task"


class Namespace(StrEnum):
    MAIN_TASK = "main-task"
    PREPARATION = "preparation"
    COMMUNITY = "community"
    MAINTENANCE = "maintenance"


class ReplyTarget(BaseModel):
    base_url: str
    request_id: str


class RequestSource(BaseModel):
    type: Literal["human", "agent"]
    id: str
    reply_to: ReplyTarget | None = None


class ReplyConfig(BaseModel):
    mode: str = "poll"


class ErrorInfo(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class RequestCreate(BaseModel):
    kind: RequestKind
    priority: int = Field(ge=0, le=100)
    source: RequestSource
    summary: str = Field(min_length=1)
    details: dict[str, Any]
    reply: ReplyConfig | None = None
    deadline: str | None = None
    idempotency_key: str | None = None
    namespace_hint: str | None = None
    activity_id: str | None = None

    model_config = ConfigDict(extra="forbid")


class RequestAccepted(BaseModel):
    request_id: str
    status: RequestStatus
    accepted_at: str


class RequestRecord(BaseModel):
    request_id: str
    status: RequestStatus
    kind: RequestKind
    priority: int
    source: RequestSource
    summary: str
    details: dict[str, Any]
    reply: ReplyConfig | None = None
    deadline: str | None = None
    namespace_hint: str | None = None
    activity_id: str | None = None
    lease_owner: str | None = None
    leased_until: str | None = None
    idempotency_key: str | None = None
    result: dict[str, Any] | None = None
    error: ErrorInfo | None = None
    created_at: str
    updated_at: str


class QueueItem(BaseModel):
    request_id: str
    kind: RequestKind
    priority: int
    status: RequestStatus
    created_at: str
    source: RequestSource


class QueueSnapshot(BaseModel):
    queued_count: int
    leased_count: int
    items: list[QueueItem]


class ActivityRecord(BaseModel):
    activity_id: str
    kind: str
    namespace: Namespace
    status: ActivityStatus
    request_ids: list[str] = Field(default_factory=list)
    session_id: str | None = None
    folder_path: str
    summary_path: str
    checkpoint_path: str
    checkpoint_version: int = 1
    created_at: str
    updated_at: str


class ActivityDetail(BaseModel):
    activity_id: str
    kind: str
    namespace: Namespace
    status: ActivityStatus
    summary: str
    session_id: str | None = None
    request_ids: list[str] = Field(default_factory=list)
    checkpoint_version: int = 1
    updated_at: str


class PeerRecord(BaseModel):
    agent_id: str
    role: str
    base_url: str
    token: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class AgentInfo(BaseModel):
    agent_id: str
    role: str
    port: int
    status: AgentStatus
    active_activity_id: str | None = None
    queue_depth: int
    current_session_id: str | None = None


@dataclass(slots=True)
class CodexTurnResult:
    session_id: str | None
    final_message: str
    raw_jsonl: list[str]
    exit_code: int
    stderr: str = ""
    error_code: str | None = None
    recoverable: bool = False
    approval_blocked: bool = False


@dataclass(slots=True)
class ActivityFiles:
    folder_path: str
    state_path: str
    summary_path: str
    checkpoint_path: str
    inbox_path: str
    artifacts_path: str
    logs_path: str


@dataclass(slots=True)
class CheckpointData:
    objective: str
    current_plan: list[str] = field(default_factory=list)
    completed_steps: list[str] = field(default_factory=list)
    pending_steps: list[str] = field(default_factory=list)
    important_files: list[str] = field(default_factory=list)
    known_constraints: list[str] = field(default_factory=list)
    next_prompt_seed: str = ""
