"""
Lumina MCP Server — JSON-RPC 2.0
Runs on port 8001 (aiohttp) alongside the main FastAPI app.
Exposes all registered MCP tools over HTTP JSON-RPC.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from aiohttp import web

from config.settings import settings
from backend.mcp.tool_registry import registry

# ── Auto-register all tools by importing their modules ────────────────────────
import backend.mcp.tools.code_tools      # noqa: F401
import backend.mcp.tools.data_tools      # noqa: F401
import backend.mcp.tools.schedule_tools  # noqa: F401
import backend.mcp.tools.search_tools    # noqa: F401

logger = logging.getLogger("lumina.mcp")

# ── JSON-RPC 2.0 error codes ─────────────────────────────────────────────────
PARSE_ERROR      = -32700
INVALID_REQUEST  = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS   = -32602
INTERNAL_ERROR   = -32603


def _success(result: Any, req_id: Any) -> Dict:
    return {"jsonrpc": "2.0", "result": result, "id": req_id}


def _error(code: int, message: str, req_id: Any = None, data: Any = None) -> Dict:
    err: Dict = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "error": err, "id": req_id}


# ── Request handlers ──────────────────────────────────────────────────────────

async def handle_rpc(request: web.Request) -> web.Response:
    """Main JSON-RPC 2.0 dispatcher."""
    try:
        body = await request.json()
    except Exception:
        return web.json_response(_error(PARSE_ERROR, "Parse error"), status=400)

    req_id = body.get("id")

    # Validate JSON-RPC envelope
    if body.get("jsonrpc") != "2.0" or "method" not in body:
        return web.json_response(_error(INVALID_REQUEST, "Invalid Request", req_id), status=400)

    method: str = body["method"]
    params: Dict[str, Any] = body.get("params") or {}

    logger.info(f"MCP call: {method}({list(params.keys())})")

    # Special built-in: list_tools
    if method == "list_tools":
        return web.json_response(_success({"tools": registry.list_tools()}, req_id))

    # Dispatch to registered tool
    if method not in registry:
        return web.json_response(
            _error(METHOD_NOT_FOUND, f"Method '{method}' not found", req_id), status=404
        )

    try:
        result = await registry.call(method, params)
        return web.json_response(_success(result, req_id))
    except TypeError as exc:
        # Invalid parameters
        return web.json_response(
            _error(INVALID_PARAMS, f"Invalid params: {exc}", req_id), status=400
        )
    except Exception as exc:
        logger.exception(f"MCP internal error in '{method}'")
        return web.json_response(
            _error(INTERNAL_ERROR, "Internal error", req_id, str(exc)), status=500
        )


async def handle_health(_: web.Request) -> web.Response:
    return web.json_response({
        "status": "ok",
        "server": "Lumina MCP Server",
        "tools": len(registry.list_tools()),
    })


async def handle_tools(_: web.Request) -> web.Response:
    """GET /tools — list available tools (non-RPC convenience endpoint)."""
    return web.json_response({"tools": registry.list_tools()})


# ── Server factory ────────────────────────────────────────────────────────────

def _build_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/",        handle_rpc)
    app.router.add_post("/rpc",     handle_rpc)
    app.router.add_get("/health",   handle_health)
    app.router.add_get("/tools",    handle_tools)
    return app


async def start_mcp_server() -> None:
    """Start the MCP HTTP server on the configured port (called as an asyncio task)."""
    app = _build_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.mcp_host, settings.mcp_port)
    await site.start()
    logger.info(
        f"✅ MCP Server running at http://{settings.mcp_host}:{settings.mcp_port}"
        f" — {len(registry.list_tools())} tools registered"
    )
    # Run forever (cancelled by the FastAPI lifespan shutdown)
    import asyncio
    await asyncio.Event().wait()


# ── Standalone entry point ────────────────────────────────────────────────────
if __name__ == "__main__":
    import asyncio
    asyncio.run(start_mcp_server())
