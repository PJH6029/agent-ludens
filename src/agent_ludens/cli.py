from __future__ import annotations

import uvicorn

from agent_ludens.app import create_app
from agent_ludens.config import AgentSettings


def main() -> None:
    settings = AgentSettings()
    app = create_app(settings=settings)
    uvicorn.run(app, host=settings.host, port=settings.port)
