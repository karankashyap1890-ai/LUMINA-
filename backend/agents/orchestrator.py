"""
Lumina — Orchestrator Agent (ADK Multi-Agent Router)
Analyses intent and routes messages to the appropriate specialist agent.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from backend.agents.base_agent import AgentResponse
from backend.agents.data_agent import DataAgent
from backend.agents.code_agent import CodeAgent
from backend.agents.schedule_agent import ScheduleAgent
from backend.agents.learning_agent import LearningAgent
from backend.agents.troubleshoot_agent import TroubleshootAgent

logger = logging.getLogger("lumina.orchestrator")

# ── Keyword routing table ─────────────────────────────────────────────────────
_ROUTING_TABLE: Dict[str, list[str]] = {
    "data": [
        "data", "csv", "analyze", "analyse", "chart", "graph", "plot",
        "visualize", "visualise", "statistics", "dataset", "dataframe",
        "pandas", "numpy", "correlation", "mean", "median", "histogram",
        "outlier", "regression", "distribution",
    ],
    "code": [
        "code", "python", "function", "debug", "error", "bug", "fix",
        "implement", "class", "variable", "syntax", "compile", "run this",
        "execute", "snippet", "script", "refactor", "unit test", "async",
        "recursion", "algorithm", "loop", "import", "module",
    ],
    "schedule": [
        "remind", "reminder", "schedule", "calendar", "task", "todo",
        "appointment", "meeting", "deadline", "upcoming", "later",
        "tomorrow", "tonight", "next week", "in an hour",
    ],
    "learn": [
        "explain", "teach", "learn", "understand", "what is", "what are",
        "how does", "concept", "tutorial", "beginner", "advanced",
        "difference between", "example of", "definition", "guide me",
        "eli5",
    ],
    "troubleshoot": [
        "problem", "issue", "troubleshoot", "solve", "broken", "not working",
        "stuck", "traceback", "exception", "wrong", "fails", "crash",
        "help me fix", "error:", "ModuleNotFoundError", "KeyError",
        "AttributeError", "TypeError", "IndexError", "ConnectionRefused",
    ],
}


class Orchestrator:
    """
    ADK-style multi-agent orchestrator.

    Responsibilities:
    - Hold references to all specialist agents
    - Route messages to the correct agent based on intent detection
    - Provide a unified error fallback
    """

    def __init__(self):
        self.agents: Dict[str, Any] = {
            "data":         DataAgent(),
            "code":         CodeAgent(),
            "schedule":     ScheduleAgent(),
            "learn":        LearningAgent(),
            "troubleshoot": TroubleshootAgent(),
        }
        logger.info(f"Orchestrator initialised with {len(self.agents)} agents")

    # ── Intent detection ──────────────────────────────────────────────────────

    def _detect_skill(self, message: str) -> str:
        """Score each skill by keyword hit count and return the winner."""
        lower = message.lower()
        scores: Dict[str, int] = {skill: 0 for skill in _ROUTING_TABLE}

        for skill, keywords in _ROUTING_TABLE.items():
            for kw in keywords:
                if kw in lower:
                    scores[skill] += 1

        best_skill = max(scores, key=lambda s: scores[s])
        best_score = scores[best_skill]

        if best_score == 0:
            # Default to learning for open-ended questions
            return "learn"

        logger.debug(f"Intent scores: {scores} → routing to '{best_skill}'")
        return best_skill

    # ── Main routing method ───────────────────────────────────────────────────

    async def route(
        self,
        message: str,
        skill: str = "auto",
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """Route a message to the appropriate agent and return its response."""

        # Resolve skill
        if skill == "auto" or skill not in self.agents:
            skill = self._detect_skill(message)

        agent = self.agents[skill]
        logger.info(f"→ {agent.emoji} {agent.name} | '{message[:60]}...' " if len(message) > 60
                    else f"→ {agent.emoji} {agent.name} | '{message}'")

        try:
            return await agent.process(message, context)
        except Exception as exc:
            logger.exception(f"Agent '{skill}' raised an unhandled exception")
            return AgentResponse(
                content=(
                    f"⚠️ **Lumina encountered an internal error**\n\n"
                    f"The **{skill}** agent failed to process your request.\n"
                    f"```\n{type(exc).__name__}: {exc}\n```\n"
                    "Please try rephrasing your message or choosing a different skill."
                ),
                agent_name="Orchestrator",
                skill="error",
                metadata={"error": str(exc), "failed_skill": skill},
            )

    # ── Introspection ─────────────────────────────────────────────────────────

    def list_agents(self) -> list[Dict[str, Any]]:
        return [agent.get_info() for agent in self.agents.values()]
