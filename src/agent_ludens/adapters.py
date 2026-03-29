from __future__ import annotations

import asyncio
import json
import shlex
from abc import ABC, abstractmethod
from typing import Any

from agent_ludens.config import AgentSettings
from agent_ludens.models import CodexTurnResult


class CodexAdapter(ABC):
    @abstractmethod
    async def run_turn(
        self,
        *,
        activity_id: str,
        prompt: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CodexTurnResult:
        raise NotImplementedError


class FakeCodexAdapter(CodexAdapter):
    async def run_turn(
        self,
        *,
        activity_id: str,
        prompt: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CodexTurnResult:
        metadata = metadata or {}
        behavior = metadata.get("fake_behavior", "success")
        delay = float(metadata.get("delay_seconds", 0.0))
        if delay > 0:
            await asyncio.sleep(delay)

        session_id = session_id or f"fake-session-{activity_id}"
        if behavior == "approval_blocked":
            return CodexTurnResult(
                session_id=session_id,
                final_message="",
                raw_jsonl=[
                    json.dumps({"type": "thread.started", "thread_id": session_id}),
                    json.dumps({"type": "turn.started"}),
                    json.dumps({"type": "turn.failed", "error": {"message": "Approval required"}}),
                ],
                exit_code=1,
                stderr="Approval required for the requested action.",
                error_code="approval_blocked",
                recoverable=False,
                approval_blocked=True,
            )
        if behavior == "recoverable_failure":
            return CodexTurnResult(
                session_id=session_id,
                final_message="",
                raw_jsonl=[
                    json.dumps({"type": "thread.started", "thread_id": session_id}),
                    json.dumps({"type": "turn.started"}),
                    json.dumps({"type": "turn.failed", "error": {"message": "Temporary adapter failure"}}),
                ],
                exit_code=1,
                stderr="Temporary adapter failure",
                error_code="temporary_failure",
                recoverable=True,
            )
        message = metadata.get("response_text") or f"Completed: {metadata.get('summary', activity_id)}"
        if metadata.get("mode") == "free_time":
            message = metadata.get("response_text") or f"Free-time quantum finished for {metadata.get('namespace', 'preparation')}"
        raw_jsonl = [
            json.dumps({"type": "thread.started", "thread_id": session_id}),
            json.dumps({"type": "turn.started"}),
            json.dumps({"type": "item.completed", "item": {"id": "item_0", "type": "agent_message", "text": message}}),
            json.dumps({"type": "turn.completed", "usage": {"input_tokens": len(prompt), "cached_input_tokens": 0, "output_tokens": len(message)}}),
        ]
        return CodexTurnResult(
            session_id=session_id,
            final_message=message,
            raw_jsonl=raw_jsonl,
            exit_code=0,
        )


class RealCodexAdapter(CodexAdapter):
    def __init__(self, settings: AgentSettings) -> None:
        self.settings = settings

    async def run_turn(
        self,
        *,
        activity_id: str,
        prompt: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CodexTurnResult:
        command = self._build_command(prompt=prompt, session_id=session_id)
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(self.settings.workspace_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await process.communicate()
        except asyncio.CancelledError:
            process.kill()
            await process.communicate()
            raise

        stdout_text = stdout.decode("utf-8")
        stderr_text = stderr.decode("utf-8")
        raw_lines = [line for line in stdout_text.splitlines() if line.strip()]
        parsed = [json.loads(line) for line in raw_lines]
        thread_id, final_message = parse_codex_events(parsed)
        exit_code = process.returncode or 0
        approval_blocked = exit_code != 0 and "approval" in stderr_text.lower()
        error_code = None
        if exit_code != 0:
            error_code = "approval_blocked" if approval_blocked else "codex_exec_failed"
        return CodexTurnResult(
            session_id=thread_id or session_id,
            final_message=final_message,
            raw_jsonl=raw_lines,
            exit_code=exit_code,
            stderr=stderr_text,
            error_code=error_code,
            recoverable=False,
            approval_blocked=approval_blocked,
        )

    def _build_command(self, *, prompt: str, session_id: str | None) -> list[str]:
        command = shlex.split(self.settings.codex_command)
        if session_id:
            command += ["exec", "resume", session_id]
        else:
            command += ["exec"]
        if self.settings.codex_profile:
            command += ["--profile", self.settings.codex_profile]
        if self.settings.codex_model:
            command += ["--model", self.settings.codex_model]
        if self.settings.codex_skip_git_repo_check:
            command += ["--skip-git-repo-check"]
        command += ["--json", prompt]
        return command


def parse_codex_events(events: list[dict[str, Any]]) -> tuple[str | None, str]:
    thread_id: str | None = None
    final_message = ""
    for event in events:
        if event.get("type") == "thread.started":
            thread_id = event.get("thread_id")
        item = event.get("item") or {}
        if event.get("type") == "item.completed" and item.get("type") == "agent_message":
            final_message = item.get("text", final_message)
    return thread_id, final_message


def build_adapter(settings: AgentSettings) -> CodexAdapter:
    if settings.adapter_mode == "real":
        return RealCodexAdapter(settings)
    return FakeCodexAdapter()
