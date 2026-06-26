"""
Lumina MCP — Tool Registry
Central register for all MCP-exposed tools. Uses a decorator pattern
so new tools can be added without modifying the server.
"""
from __future__ import annotations

import asyncio
import inspect
from typing import Any, Callable, Dict, List, Optional


class ToolDefinition:
    """Metadata + callable for a single MCP tool."""

    __slots__ = ("name", "description", "parameters", "fn")

    def __init__(self, name: str, description: str, parameters: Dict[str, Any], fn: Callable):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.fn = fn

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class ToolRegistry:
    """Central registry for Lumina MCP tools."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Callable:
        """Decorator to register a coroutine as an MCP tool."""
        def decorator(fn: Callable) -> Callable:
            self._tools[name] = ToolDefinition(
                name=name,
                description=description,
                parameters=parameters or {},
                fn=fn,
            )
            return fn
        return decorator

    async def call(self, name: str, params: Dict[str, Any]) -> Any:
        """Dispatch a tool call by name."""
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Unknown tool: '{name}'")
        if asyncio.iscoroutinefunction(tool.fn):
            return await tool.fn(**params)
        return tool.fn(**params)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._tools.values()]

    def __contains__(self, name: str) -> bool:
        return name in self._tools


# ── Singleton ────────────────────────────────────────────────────────────────
registry = ToolRegistry()
