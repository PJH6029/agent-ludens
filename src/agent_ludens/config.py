from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    agent_id: str = Field(default="writer-7101", alias="AGENT_LUDENS_AGENT_ID")
    role: str = Field(default="writer", alias="AGENT_LUDENS_ROLE")
    host: str = Field(default="127.0.0.1", alias="AGENT_LUDENS_HOST")
    port: int = Field(default=7101, alias="AGENT_LUDENS_PORT")
    task_memory_root: Path = Field(default=Path(".task-memory"), alias="AGENT_LUDENS_TASK_MEMORY_ROOT")
    auth_token: str | None = Field(default=None, alias="AGENT_LUDENS_AUTH_TOKEN")
    poll_interval_seconds: float = Field(default=0.1, alias="AGENT_LUDENS_POLL_INTERVAL_SECONDS")
    request_lease_ttl_seconds: int = Field(default=30, alias="AGENT_LUDENS_REQUEST_LEASE_TTL_SECONDS")
    enable_supervisor: bool = Field(default=True, alias="AGENT_LUDENS_ENABLE_SUPERVISOR")
    enable_free_time: bool = Field(default=True, alias="AGENT_LUDENS_ENABLE_FREE_TIME")
    free_time_delay_seconds: float = Field(default=0.2, alias="AGENT_LUDENS_FREE_TIME_DELAY_SECONDS")
    adapter_mode: str = Field(default="fake", alias="AGENT_LUDENS_ADAPTER_MODE")
    codex_command: str = Field(default="codex", alias="AGENT_LUDENS_CODEX_COMMAND")
    codex_profile: str | None = Field(default=None, alias="AGENT_LUDENS_CODEX_PROFILE")
    codex_model: str | None = Field(default=None, alias="AGENT_LUDENS_CODEX_MODEL")
    codex_skip_git_repo_check: bool = Field(default=False, alias="AGENT_LUDENS_CODEX_SKIP_GIT_REPO_CHECK")
    workspace_root: Path = Field(default=Path("."), alias="AGENT_LUDENS_WORKSPACE_ROOT")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def database_path(self) -> Path:
        return self.task_memory_root / "requests.sqlite"

    @property
    def session_map_path(self) -> Path:
        return self.task_memory_root / "session_map.json"

    @property
    def runtime_dir(self) -> Path:
        return self.task_memory_root / "runtime"
