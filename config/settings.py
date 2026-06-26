"""
Lumina AI Agent System — Configuration

All intelligence is self-contained: no external API keys are required.
Agents use built-in knowledge bases, AST analysis, and rule-based engines.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────
    app_name: str = "Lumina AI Agent System"
    app_version: str = "1.0.0"
    debug: bool = False

    # ── Server ───────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8001

    # ── Security ─────────────────────────────────────────────
    # JWT signing key — override via SECRET_KEY env var in production
    secret_key: str = "lumina-secret-key-CHANGE-IN-PRODUCTION-use-32-char-min"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # ── Limits ───────────────────────────────────────────────
    max_requests_per_minute: int = 60
    max_code_execution_timeout: int = 10
    max_message_length: int = 10000
    max_response_length: int = 8000

    # ── Database ─────────────────────────────────────────────
    db_path: str = "data/lumina.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
