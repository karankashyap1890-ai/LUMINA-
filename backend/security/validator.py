"""
Lumina Security — Input Validation
Pydantic v2 models for all incoming requests with sanitization.
"""
import re
import html
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, Any, Dict


class ChatRequest(BaseModel):
    """Validated incoming chat message."""
    message: str = Field(..., min_length=1, max_length=10_000, description="User message")
    skill: Optional[Literal["auto", "data", "code", "schedule", "learn", "troubleshoot"]] = "auto"
    context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = Field(None, max_length=64)

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        v = re.sub(r"<[^>]+>", "", v)          # strip HTML tags
        v = v.replace("\x00", "")               # remove null bytes
        v = re.sub(r"\s{3,}", "  ", v).strip()  # collapse excessive whitespace
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(r"^[a-zA-Z0-9\-_]{4,64}$", v):
            raise ValueError("session_id contains invalid characters")
        return v


class CodeExecutionRequest(BaseModel):
    """Validated code execution request."""
    code: str = Field(..., min_length=1, max_length=5_000)
    language: str = Field(default="python", pattern=r"^python$")  # only python for now

    @field_validator("code")
    @classmethod
    def no_null_bytes(cls, v: str) -> str:
        return v.replace("\x00", "")


class ScheduleRequest(BaseModel):
    """Validated reminder creation request."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1_000)
    remind_at: Optional[str] = Field(None, max_length=50)

    @field_validator("title", "description")
    @classmethod
    def escape_html(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return html.escape(v.strip())
        return v


class TokenRequest(BaseModel):
    """Login credentials."""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)


class MCPRequest(BaseModel):
    """JSON-RPC 2.0 MCP request."""
    jsonrpc: str = Field("2.0", pattern=r"^2\.0$")
    method: str = Field(..., min_length=1, max_length=100)
    params: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None
