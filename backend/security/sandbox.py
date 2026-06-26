"""
Lumina Security — Code Sandbox
Two-stage protection: AST-level static analysis + subprocess isolation.
"""
import ast
import os
import sys
import subprocess
import tempfile
import time
from typing import Any, Dict, Set

from config.settings import settings
import logging

logger = logging.getLogger(__name__)


# ── Deny-lists ───────────────────────────────────────────────────────────────

FORBIDDEN_MODULES: Set[str] = {
    "os", "sys", "subprocess", "shutil", "socket", "requests",
    "urllib", "http", "ftplib", "smtplib", "pickle", "shelve",
    "importlib", "ctypes", "threading", "multiprocessing",
    "signal", "pty", "atexit", "gc", "pathlib", "glob",
}

FORBIDDEN_CALLS: Set[str] = {
    "exec", "eval", "compile", "__import__", "open", "input",
    "breakpoint", "vars", "dir", "globals", "locals",
    "delattr", "setattr",
}

FORBIDDEN_DUNDER: Set[str] = {
    "__class__", "__bases__", "__subclasses__", "__globals__",
    "__builtins__", "__code__", "__closure__", "__reduce__",
}


class SecurityError(Exception):
    """Raised when code fails static security validation."""


# ── Stage 1: AST Validation ──────────────────────────────────────────────────

def validate_ast(code: str) -> None:
    """Walk the AST and raise SecurityError on forbidden constructs."""
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise SecurityError(f"Syntax error at line {exc.lineno}: {exc.msg}")

    for node in ast.walk(tree):
        # Forbidden imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in FORBIDDEN_MODULES:
                    raise SecurityError(f"Import of '{top}' is blocked in sandbox")

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top in FORBIDDEN_MODULES:
                    raise SecurityError(f"Import from '{top}' is blocked in sandbox")

        # Forbidden function calls
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                raise SecurityError(f"Call to '{node.func.id}' is blocked in sandbox")
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in {"system", "popen", "exec", "eval", "spawn"}:
                    raise SecurityError(f"Method '{node.func.attr}' is blocked in sandbox")

        # Dangerous dunder attribute access
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_DUNDER:
                raise SecurityError(f"Access to '{node.attr}' is blocked in sandbox")


# ── Stage 2: Subprocess Isolation ────────────────────────────────────────────

_SANDBOX_HEADER = """\
import sys as _sys
# Block sensitive modules at import time
for _mod in ['os','subprocess','socket','shutil','signal','ctypes','threading']:
    _sys.modules[_mod] = None

"""


async def execute_code_safely(code: str, timeout: int = None) -> Dict[str, Any]:
    """
    Execute Python code in a sandboxed subprocess.

    Returns a dict with keys:
        success, output, error, execution_time, security_blocked
    """
    timeout = timeout or settings.max_code_execution_timeout
    t0 = time.monotonic()

    # ── Stage 1: static analysis ─────────────────────────────────────────────
    try:
        validate_ast(code)
    except SecurityError as exc:
        return {
            "success": False,
            "output": "",
            "error": f"🔒 Security block: {exc}",
            "execution_time": 0.0,
            "security_blocked": True,
        }

    # ── Stage 2: subprocess execution ────────────────────────────────────────
    wrapped = _SANDBOX_HEADER + code
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(wrapped)
            tmp_path = fh.name

        proc = subprocess.run(
            [sys.executable, "-u", tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tempfile.gettempdir(),
            env={"PATH": os.environ.get("PATH", ""), "PYTHONPATH": ""},
        )
        elapsed = round(time.monotonic() - t0, 3)
        return {
            "success": proc.returncode == 0,
            "output": proc.stdout[:3_000],
            "error": proc.stderr[:1_000] if proc.stderr else "",
            "return_code": proc.returncode,
            "execution_time": elapsed,
            "security_blocked": False,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": f"⏱️ Timed out after {timeout}s",
            "execution_time": float(timeout),
            "security_blocked": False,
        }
    except Exception as exc:
        logger.exception("Sandbox execution error")
        return {
            "success": False,
            "output": "",
            "error": str(exc),
            "execution_time": round(time.monotonic() - t0, 3),
            "security_blocked": False,
        }
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
