"""
Lumina Agents — Abstract Base Agent
All specialist agents inherit from BaseAgent.

NO EXTERNAL API KEYS ARE USED.
All intelligence is fully self-contained:
  - Built-in knowledge bases   (hardcoded expert content per skill)
  - AST-based code analysis    (code review & sandbox)
  - Rule/pattern-matching      (error diagnosis, scheduling)
  - SQLite persistence         (scheduler reminders)
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AgentResponse:
    """Standardised response envelope returned by every Lumina agent."""

    __slots__ = ("content", "agent_name", "skill", "tools_used", "metadata", "confidence")

    def __init__(
        self,
        content: str,
        agent_name: str,
        skill: str,
        tools_used: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
    ):
        self.content = content
        self.agent_name = agent_name
        self.skill = skill
        self.tools_used: List[str] = tools_used or []
        self.metadata: Dict[str, Any] = metadata or {}
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "agent_name": self.agent_name,
            "skill": self.skill,
            "tools_used": self.tools_used,
            "metadata": self.metadata,
            "confidence": self.confidence,
        }


class BaseAgent(ABC):
    """Abstract base for all Lumina specialist agents.

    Design principle: ALL intelligence is self-contained.
    No external APIs, no API keys, no network calls to any LLM provider.
    Each specialist agent implements its own local reasoning engine.
    """

    def __init__(self, name: str, skill: str, description: str, emoji: str = "🤖"):
        self.name = name
        self.skill = skill
        self.description = description
        self.emoji = emoji
        self.logger = logging.getLogger(f"lumina.agent.{name.lower()}")
        self.logger.info(f"{emoji} {name} ready — self-contained, no API key required")

    # ── Required interface ────────────────────────────────────────────────────

    @abstractmethod
    async def process(self, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Process a user message and return an AgentResponse."""

    # ── Introspection ─────────────────────────────────────────────────────────

    def get_info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "skill": self.skill,
            "description": self.description,
            "emoji": self.emoji,
            "mode": "self-contained",
        }
