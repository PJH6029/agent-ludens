from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response
import pathlib

from agent_ludens.config import AgentSettings
from agent_ludens.models import ActivityStatus, ErrorInfo, PeerRecord, RequestCreate
from agent_ludens.store import ConflictError
from agent_ludens.supervisor import AgentRuntime


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self.error = ErrorInfo(code=code, message=message, details=details or {})
        super().__init__(message)


def create_app(settings: AgentSettings | None = None, runtime: AgentRuntime | None = None) -> FastAPI:
    settings = settings or AgentSettings()
    runtime = runtime or AgentRuntime(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> Any:
        await runtime.start()
        try:
            yield
        finally:
            await runtime.shutdown()

    app = FastAPI(title="Agent Ludens", lifespan=lifespan)
    app.state.runtime = runtime
    app.state.settings = settings

    @app.exception_handler(ApiError)
    async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"error": exc.error.model_dump(mode="json")})

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        error = ErrorInfo(code="invalid_request", message="Invalid request payload", details={"errors": exc.errors()})
        return JSONResponse(status_code=422, content={"error": error.model_dump(mode="json")})

    @app.middleware("http")
    async def auth_middleware(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.url.path == "/healthz":
            return await call_next(request)
        token = settings.auth_token
        if token:
            header_token = request.headers.get("X-Agent-Token")
            if header_token != token:
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": ErrorInfo(code="unauthorized", message="Missing or invalid X-Agent-Token").model_dump(mode="json")
                    },
                )
        return await call_next(request)

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        return runtime.health()

    @app.get("/v1/agent")
    async def agent() -> dict[str, Any]:
        return runtime.agent_info().model_dump(mode="json")

    @app.get("/v1/queue")
    async def queue() -> dict[str, Any]:
        return runtime.store.get_queue_snapshot().model_dump(mode="json")

    @app.get("/v1/events")
    async def events(limit: int = 50) -> list[dict[str, Any]]:
        return runtime.list_recent_events(limit=limit)

    @app.post("/v1/requests", status_code=202)
    async def create_request(payload: RequestCreate) -> dict[str, Any]:
        try:
            accepted = runtime.store.insert_request(payload)
        except ConflictError as exc:
            raise ApiError(409, "conflict", str(exc)) from exc
        runtime.wakeup()
        return accepted.model_dump(mode="json")

    @app.get("/v1/requests/{request_id}")
    async def get_request(request_id: str) -> dict[str, Any]:
        request_record = runtime.store.get_request(request_id)
        if request_record is None:
            raise ApiError(404, "not_found", f"Request {request_id} was not found")
        return request_record.model_dump(mode="json")

    @app.post("/v1/requests/{request_id}/cancel")
    async def cancel_request(request_id: str) -> dict[str, Any]:
        updated = runtime.store.cancel_request(request_id)
        if updated is None:
            raise ApiError(404, "not_found", f"Request {request_id} was not found")
        await runtime.request_cancellation(request_id)
        return {"request_id": updated.request_id, "status": updated.status}

    @app.get("/v1/activities")
    async def list_activities(status: ActivityStatus | None = None, namespace: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        return [detail.model_dump(mode="json") for detail in runtime.list_activity_details(status=status, namespace=namespace, limit=limit)]

    @app.get("/v1/activities/{activity_id}")
    async def get_activity(activity_id: str) -> dict[str, Any]:
        try:
            detail = runtime.get_activity_detail(activity_id)
        except KeyError as exc:
            raise ApiError(404, "not_found", f"Activity {activity_id} was not found") from exc
        return detail.model_dump(mode="json")

    @app.get("/v1/peers")
    async def list_peers() -> list[dict[str, Any]]:
        return [peer.model_dump(mode="json") for peer in runtime.store.list_peers()]

    @app.post("/v1/peers", status_code=201)
    async def register_peer(peer: PeerRecord) -> dict[str, Any]:
        return runtime.store.upsert_peer(peer).model_dump(mode="json")

    ui_dir = pathlib.Path(__file__).parent / "ui"
    app.mount("/ui", StaticFiles(directory=str(ui_dir)), name="ui")

    @app.get("/")
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/ui/index.html")

    return app
