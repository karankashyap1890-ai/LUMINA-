"""
Lumina Agent — Troubleshooter
Analyses errors and provides structured root-cause + resolution strategies.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from backend.agents.base_agent import BaseAgent, AgentResponse


# Common error pattern database
_ERROR_PATTERNS: Dict[str, Dict[str, str]] = {
    "ModuleNotFoundError": {
        "cause": "Python cannot find the package you're importing.",
        "fix": (
            "1. Install the package: `pip install <package_name>`\n"
            "2. Verify you're in the right virtual environment: `pip list | grep <package>`\n"
            "3. Check spelling — the import name may differ from the install name\n"
            "   (e.g. `pip install Pillow` but `import PIL`)"
        ),
    },
    "KeyError": {
        "cause": "You're accessing a dictionary key that doesn't exist.",
        "fix": (
            "1. Use `.get(key, default)` instead of `dict[key]`\n"
            "2. Check key existence: `if key in dict:`\n"
            "3. Print `dict.keys()` to see available keys"
        ),
    },
    "AttributeError": {
        "cause": "You're accessing an attribute or method that the object doesn't have.",
        "fix": (
            "1. Use `dir(obj)` to list available attributes\n"
            "2. Check for typos in the attribute name\n"
            "3. Verify the object type with `type(obj)`\n"
            "4. Ensure the object was properly initialised (not `None`)"
        ),
    },
    "TypeError": {
        "cause": "An operation was applied to an incompatible type.",
        "fix": (
            "1. Check the types of your variables: `print(type(var))`\n"
            "2. Ensure function arguments match the expected types\n"
            "3. Convert types explicitly: `str()`, `int()`, `float()`"
        ),
    },
    "IndexError": {
        "cause": "You're accessing a list/tuple at an index that's out of range.",
        "fix": (
            "1. Check the list length first: `len(my_list)`\n"
            "2. Access within bounds: `if i < len(my_list):`\n"
            "3. Use negative indexing carefully: `-1` is the last element"
        ),
    },
    "ConnectionRefusedError": {
        "cause": "The target host rejected the connection — the service may not be running.",
        "fix": (
            "1. Verify the service is running: `curl http://localhost:8000/health`\n"
            "2. Check the host and port are correct\n"
            "3. Check firewall rules allow the connection\n"
            "4. Look at the service logs for startup errors"
        ),
    },
    "PermissionError": {
        "cause": "The process lacks permission to access a file or resource.",
        "fix": (
            "1. Check file ownership: `ls -la <file>`\n"
            "2. Fix permissions: `chmod +r <file>` or `chmod +x <script>`\n"
            "3. Run with elevated privileges only if absolutely necessary\n"
            "4. Ensure the path exists and is correct"
        ),
    },
    "RecursionError": {
        "cause": "Recursion depth exceeded Python's limit (~1000 frames).",
        "fix": (
            "1. Add or fix the base case to terminate recursion\n"
            "2. Temporarily increase limit: `sys.setrecursionlimit(5000)`\n"
            "3. Refactor to an iterative approach using an explicit stack"
        ),
    },
}


class TroubleshootAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Troubleshooter",
            skill="troubleshoot",
            description="Diagnoses errors, finds root causes, and guides you step-by-step to resolution",
            emoji="🔧",
        )

    # ── Pattern matching ──────────────────────────────────────────────────────

    def _match_error(self, text: str) -> Optional[Dict[str, str]]:
        for pattern, info in _ERROR_PATTERNS.items():
            if pattern in text:
                return {"error_type": pattern, **info}
        return None

    # ── Response builder ──────────────────────────────────────────────────────

    @staticmethod
    def _format_error_response(match: Dict[str, str], original: str) -> str:
        return (
            f"### 🔴 Error Detected: `{match['error_type']}`\n\n"
            f"**Root Cause:** {match['cause']}\n\n"
            f"**Resolution Steps:**\n{match['fix']}\n\n"
            "---\n"
            "### 🔍 General Debugging Checklist\n"
            "- [ ] Read the full traceback from the **bottom up**\n"
            "- [ ] Identify the exact line where the error occurred\n"
            "- [ ] Add `print()` statements to inspect variable values\n"
            "- [ ] Check recent changes that may have introduced the bug\n"
            "- [ ] Search the error message on Stack Overflow / GitHub Issues"
        )

    @staticmethod
    def _generic_troubleshoot() -> str:
        return (
            "**🔧 Lumina Troubleshooter**\n\n"
            "Share your error message or describe the problem and I'll help you:\n\n"
            "**1. Identify root cause** — What's actually going wrong?\n"
            "**2. Systematic diagnosis** — Step-by-step isolation\n"
            "**3. Resolution strategy** — Concrete fix with code examples\n"
            "**4. Prevention** — How to avoid this in the future\n\n"
            "**Paste your error:**\n"
            "```\nTraceback (most recent call last):\n  ...\nModuleNotFoundError: No module named 'xyz'\n```"
        )

    # ── Main entry point ──────────────────────────────────────────────────────

    async def process(self, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        tools_used: List[str] = []

        # Check for known error patterns
        error_match = self._match_error(message)

        if error_match:
            content = self._format_error_response(error_match, message)
            tools_used.append("error_pattern_db")

            # Pattern matched — structured response is complete

        else:
            # General troubleshooting — use built-in checklist
            content = self._generic_troubleshoot()
            tools_used.append("fallback_engine")

        return AgentResponse(
            content=content,
            agent_name=self.name,
            skill=self.skill,
            tools_used=tools_used,
            metadata={"matched_error": error_match.get("error_type") if error_match else None},
        )
