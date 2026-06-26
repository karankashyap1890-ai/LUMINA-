"""
Tests — Security Layer
Validates input sanitisation, sandbox blocking, and rate limiting.
"""
import asyncio
import pytest
from backend.security.validator import ChatRequest, CodeExecutionRequest
from backend.security.sandbox import validate_ast, SecurityError
from backend.security.auth import create_access_token, verify_token
from backend.security.rate_limiter import SlidingWindowRateLimiter


# ── Validator tests ──────────────────────────────────────────────────────────

def test_chat_request_strips_html():
    req = ChatRequest(message="<script>alert(1)</script>Hello")
    assert "<script>" not in req.message
    assert "Hello" in req.message


def test_chat_request_too_long():
    with pytest.raises(Exception):
        ChatRequest(message="x" * 10_001)


def test_chat_request_valid_skills():
    for skill in ["auto", "data", "code", "schedule", "learn", "troubleshoot"]:
        req = ChatRequest(message="test", skill=skill)
        assert req.skill == skill


def test_code_request_max_length():
    with pytest.raises(Exception):
        CodeExecutionRequest(code="x" * 5_001)


# ── Sandbox tests ────────────────────────────────────────────────────────────

def test_sandbox_blocks_os_import():
    with pytest.raises(SecurityError, match="os"):
        validate_ast("import os\nos.system('ls')")


def test_sandbox_blocks_subprocess():
    with pytest.raises(SecurityError):
        validate_ast("import subprocess\nsubprocess.run(['rm', '-rf', '/'])")


def test_sandbox_blocks_eval():
    with pytest.raises(SecurityError, match="eval"):
        validate_ast("eval('__import__(\"os\").system(\"ls\")')")


def test_sandbox_blocks_exec():
    with pytest.raises(SecurityError, match="exec"):
        validate_ast("exec('import os')")


def test_sandbox_allows_safe_code():
    # Should NOT raise
    validate_ast("x = [i**2 for i in range(10)]\nprint(sum(x))")


def test_sandbox_allows_math():
    validate_ast("import math\nprint(math.pi)")


def test_sandbox_syntax_error():
    with pytest.raises(SecurityError, match="Syntax"):
        validate_ast("def foo(\n  pass")


@pytest.mark.asyncio
async def test_sandbox_executes_simple_code():
    from backend.security.sandbox import execute_code_safely
    result = await execute_code_safely("print('hello lumina')")
    assert result["success"] is True
    assert "hello lumina" in result["output"]


@pytest.mark.asyncio
async def test_sandbox_timeout():
    from backend.security.sandbox import execute_code_safely
    result = await execute_code_safely("while True: pass", timeout=1)
    assert result["success"] is False
    assert "Timed out" in result["error"]


# ── Auth tests ───────────────────────────────────────────────────────────────

def test_token_roundtrip():
    token = create_access_token({"sub": "testuser", "role": "admin"})
    payload = verify_token(token)
    assert payload is not None
    assert payload["sub"] == "testuser"
    assert payload["role"] == "admin"


def test_invalid_token():
    result = verify_token("this.is.not.valid")
    assert result is None


def test_tampered_token():
    token = create_access_token({"sub": "alice"})
    tampered = token[:-5] + "ZZZZZ"
    assert verify_token(tampered) is None


# ── Rate limiter tests ───────────────────────────────────────────────────────

def test_rate_limiter_allows_under_limit():
    limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=60)
    for _ in range(5):
        assert limiter.is_allowed("test_ip") is True


def test_rate_limiter_blocks_over_limit():
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        limiter.is_allowed("ip1")
    assert limiter.is_allowed("ip1") is False


def test_rate_limiter_different_ips():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60)
    assert limiter.is_allowed("ip_a") is True
    assert limiter.is_allowed("ip_a") is True
    assert limiter.is_allowed("ip_a") is False  # ip_a blocked
    assert limiter.is_allowed("ip_b") is True   # ip_b still allowed


def test_rate_limiter_reset():
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=60)
    limiter.is_allowed("ip_x")
    assert limiter.is_allowed("ip_x") is False
    limiter.reset("ip_x")
    assert limiter.is_allowed("ip_x") is True
