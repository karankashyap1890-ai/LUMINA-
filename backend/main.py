"""
Lumina — FastAPI Application Entry Point
Serves the REST API, WebSocket endpoint, and static frontend.
Launches the MCP server as a background asyncio task.
"""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from backend.agents.orchestrator import Orchestrator
from backend.mcp.mcp_server import start_mcp_server
from backend.security.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
)
from backend.security.rate_limiter import check_rate_limit
from backend.security.validator import ChatRequest, CodeExecutionRequest, TokenRequest

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("lumina.api")

# ── Orchestrator (singleton) ──────────────────────────────────────────────────
orchestrator = Orchestrator()


# ── App lifespan ──────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("━" * 60)
    logger.info("🌟  LUMINA AI AGENT SYSTEM — STARTING UP")
    logger.info("━" * 60)

    # Create data directory for SQLite
    os.makedirs("data", exist_ok=True)

    # Start MCP server in background
    mcp_task = asyncio.create_task(start_mcp_server())
    logger.info(f"🔌  MCP Server launching on port {settings.mcp_port} ...")

    yield  # ← app is live

    # Shutdown
    mcp_task.cancel()
    try:
        await mcp_task
    except asyncio.CancelledError:
        pass
    logger.info("👋  Lumina shut down cleanly.")


# ── FastAPI instance ──────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    description=(
        "Full-stack multi-agent AI system featuring 5 specialist agents, "
        "an MCP server, JWT auth, sandboxed code execution, and a premium UI."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files (frontend) ───────────────────────────────────────────────────
_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(_FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=_FRONTEND_DIR), name="static")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Routes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/", include_in_schema=False)
async def root():
    """Serve the frontend SPA."""
    index = os.path.join(_FRONTEND_DIR, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return JSONResponse({"message": "Lumina API is running", "docs": "/docs"})


@app.get("/health", tags=["System"])
async def health() -> Dict[str, Any]:
    """System health check — also shows all registered agents."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "mode": "self-contained (no API keys required)",
        "agents": orchestrator.list_agents(),
        "mcp_url": f"http://localhost:{settings.mcp_port}",
    }


# ── Auth ──────────────────────────────────────────────────────────────────────
@app.post("/api/token", tags=["Auth"])
async def login(body: TokenRequest):
    """Exchange credentials for a JWT bearer token."""
    user = authenticate_user(body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token({"sub": user["username"], "role": user["role"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "username": user["username"],
    }


# ── Chat (REST) ───────────────────────────────────────────────────────────────
@app.post("/api/chat", tags=["Chat"], dependencies=[Depends(check_rate_limit)])
async def chat(
    body: ChatRequest,
    user: Dict = Depends(get_current_user),
):
    """Send a message to the orchestrator and receive an agent response."""
    try:
        response = await orchestrator.route(
            message=body.message,
            skill=body.skill or "auto",
            context={"user": user, **(body.context or {})},
        )
        return response.to_dict()
    except Exception as exc:
        logger.exception("Unhandled chat error")
        raise HTTPException(status_code=500, detail=str(exc))


# ── Code execution (REST) ─────────────────────────────────────────────────────
@app.post("/api/execute", tags=["Code"], dependencies=[Depends(check_rate_limit)])
async def execute_code(body: CodeExecutionRequest):
    """Execute Python code in the Lumina sandbox."""
    from backend.security.sandbox import execute_code_safely
    result = await execute_code_safely(body.code)
    return result


# ── Agents info ───────────────────────────────────────────────────────────────
@app.get("/api/agents", tags=["System"])
async def get_agents():
    """List all specialist agents and their current status."""
    return {"agents": orchestrator.list_agents()}


# ── Reminders (REST) ──────────────────────────────────────────────────────────
@app.get("/api/reminders", tags=["Schedule"], dependencies=[Depends(check_rate_limit)])
async def get_reminders():
    """List all active reminders."""
    agent = orchestrator.agents.get("schedule")
    if agent:
        return {"reminders": await agent.get_all_reminders()}
    return {"reminders": []}


# ── MCP proxy (optional REST bridge) ─────────────────────────────────────────
@app.post("/api/mcp", tags=["MCP"], dependencies=[Depends(check_rate_limit)])
async def mcp_proxy(body: Dict[str, Any]):
    """
    Proxy JSON-RPC 2.0 calls to the MCP server.
    Allows the frontend to call MCP tools without CORS issues.
    """
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"http://localhost:{settings.mcp_port}/rpc",
                json=body,
            )
            return resp.json()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"MCP server unreachable: {exc}")


# ── WebSocket ─────────────────────────────────────────────────────────────────
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    Real-time chat via WebSocket.

    Client sends: {"message": "...", "skill": "auto"}
    Server sends: {"type": "response", "data": AgentResponse}
    """
    await websocket.accept()
    logger.info(f"WebSocket connected: session={session_id}")

    try:
        while True:
            raw = await websocket.receive_json()
            message: str = str(raw.get("message", "")).strip()
            skill: str   = raw.get("skill", "auto")

            if not message:
                await websocket.send_json({"type": "error", "message": "Empty message"})
                continue

            # Send typing indicator
            await websocket.send_json({"type": "typing", "agent": skill})

            try:
                response = await orchestrator.route(message=message, skill=skill)
                await websocket.send_json(
                    {"type": "response", "data": response.to_dict(), "session_id": session_id}
                )
            except Exception as exc:
                logger.error(f"WS agent error: {exc}")
                await websocket.send_json(
                    {"type": "error", "message": f"Agent error: {exc}"}
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: session={session_id}")
    except Exception as exc:
        logger.error(f"WebSocket fatal error: {exc}")


# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
