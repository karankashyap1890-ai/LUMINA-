"""
Lumina MCP Tools — Search / Lookup Tools
Concept explanations and troubleshooting lookups exposed over MCP.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.mcp.tool_registry import registry


@registry.register(
    name="explain_concept",
    description="Explain a programming or technical concept at a given knowledge level.",
    parameters={
        "type": "object",
        "properties": {
            "concept": {"type": "string", "description": "The concept or topic to explain"},
            "level":   {"type": "string", "enum": ["beginner", "intermediate", "advanced"],
                        "description": "Target knowledge level"},
        },
        "required": ["concept"],
    },
)
async def explain_concept(concept: str, level: str = "intermediate") -> Dict[str, Any]:
    """Look up concept in the LearningAgent knowledge base."""
    from backend.agents.learning_agent import _KNOWLEDGE_BASE

    kb_entry = _KNOWLEDGE_BASE.get(concept.lower())
    if kb_entry:
        return {
            "concept": concept,
            "level": level,
            "explanation": kb_entry.get(level, kb_entry.get("intermediate", "")),
            "source": "knowledge_base",
        }

    return {
        "concept": concept,
        "level": level,
        "explanation": (
            f"The concept '{concept}' was not found in the offline knowledge base. "
            "Try asking the LearningAgent directly for an AI-powered explanation."
        ),
        "source": "not_found",
    }


@registry.register(
    name="lookup_error",
    description="Look up a Python exception type and return its root cause and fix.",
    parameters={
        "type": "object",
        "properties": {
            "error_name": {"type": "string", "description": "Exception class name (e.g. 'KeyError')"},
        },
        "required": ["error_name"],
    },
)
async def lookup_error(error_name: str) -> Dict[str, Any]:
    """Return structured fix info for a known Python exception."""
    from backend.agents.troubleshoot_agent import _ERROR_PATTERNS

    info = _ERROR_PATTERNS.get(error_name)
    if info:
        return {"found": True, "error_name": error_name, **info}

    return {
        "found": False,
        "error_name": error_name,
        "cause": "Not in the error database.",
        "fix": (
            "1. Read the full traceback\n"
            "2. Search the error on Stack Overflow\n"
            "3. Check the official Python docs"
        ),
    }


@registry.register(
    name="system_status",
    description="Return current Lumina system health and agent status.",
    parameters={"type": "object", "properties": {}, "required": []},
)
async def system_status() -> Dict[str, Any]:
    """Return a health snapshot of the Lumina system."""
    import platform
    from config.settings import settings

    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "platform": platform.system(),
        "python": platform.python_version(),
        "mode": "self-contained (no API keys required)",
        "mcp_port": settings.mcp_port,
        "api_port": settings.api_port,
    }
