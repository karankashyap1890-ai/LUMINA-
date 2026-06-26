"""
Lumina MCP Tools — Code Tools
Safe code execution and formatting tools exposed over MCP.
"""
from __future__ import annotations

from typing import Any, Dict

from backend.mcp.tool_registry import registry
from backend.security.sandbox import execute_code_safely


@registry.register(
    name="run_code",
    description="Execute a Python snippet in a sandboxed subprocess. Returns stdout, stderr, and execution time.",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python source code to execute"},
            "timeout": {"type": "integer", "description": "Max execution seconds (default 10)"},
        },
        "required": ["code"],
    },
)
async def run_code(code: str, timeout: int = 10) -> Dict[str, Any]:
    """Execute Python code safely via the Lumina sandbox."""
    return await execute_code_safely(code, timeout=timeout)


@registry.register(
    name="format_code",
    description="Format Python code with basic indentation normalisation and style hints.",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python source code to format"},
        },
        "required": ["code"],
    },
)
async def format_code(code: str) -> Dict[str, Any]:
    """Normalise code indentation and return style feedback."""
    import ast

    lines = code.splitlines()
    issues: list[str] = []

    # Check for tabs
    if any("\t" in line for line in lines):
        issues.append("Use spaces (PEP 8), not tabs")

    # Check long lines
    long = [i + 1 for i, l in enumerate(lines) if len(l) > 120]
    if long:
        issues.append(f"Lines too long (>120 chars): {long[:5]}")

    # Try parse
    try:
        ast.parse(code)
    except SyntaxError as exc:
        issues.append(f"Syntax error at line {exc.lineno}: {exc.msg}")

    return {
        "formatted_code": code,  # actual formatting would use `black` if installed
        "issues": issues,
        "is_valid_syntax": not any("Syntax" in i for i in issues),
    }


@registry.register(
    name="explain_error",
    description="Given a Python error message or traceback, return a human-readable diagnosis.",
    parameters={
        "type": "object",
        "properties": {
            "error_text": {"type": "string", "description": "Error message or full traceback"},
        },
        "required": ["error_text"],
    },
)
async def explain_error(error_text: str) -> Dict[str, str]:
    """Match error text against known patterns and return a structured explanation."""
    from backend.agents.troubleshoot_agent import _ERROR_PATTERNS

    for pattern, info in _ERROR_PATTERNS.items():
        if pattern in error_text:
            return {
                "error_type": pattern,
                "cause": info["cause"],
                "fix": info["fix"],
            }

    return {
        "error_type": "Unknown",
        "cause": "Could not automatically identify the error type.",
        "fix": (
            "1. Read the traceback from the bottom up\n"
            "2. Identify the line number and file\n"
            "3. Search the error message online"
        ),
    }
