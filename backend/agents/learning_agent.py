"""
Lumina Agent — Personalized Learning
Adapts explanations to the detected knowledge level of the user.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from backend.agents.base_agent import BaseAgent, AgentResponse


# Concept knowledge-base for offline mode
_KNOWLEDGE_BASE: Dict[str, Dict[str, str]] = {
    "recursion": {
        "beginner": (
            "**Recursion** means a function calls *itself* to solve a smaller version of the same problem.\n\n"
            "Think of Russian nesting dolls 🪆 — each doll contains a smaller one until you reach the smallest.\n\n"
            "```python\ndef countdown(n):\n    if n == 0:       # base case — stop!\n        print('Done!')\n    else:\n        print(n)\n        countdown(n - 1)  # call itself with smaller n\n\ncountdown(3)\n# 3, 2, 1, Done!\n```"
        ),
        "intermediate": (
            "**Recursion** decomposes a problem into sub-problems of the same type.\n\n"
            "Key parts: **base case** (terminates recursion) + **recursive case** (reduces problem size).\n\n"
            "```python\ndef factorial(n):\n    if n <= 1: return 1          # base case\n    return n * factorial(n - 1)  # recursive case\n```\n\n"
            "⚠️ Watch for stack overflow — Python's limit is 1000 frames by default."
        ),
        "advanced": (
            "**Recursion** in Python uses the call stack — each frame stores local state.\n\n"
            "Trade-offs vs iteration:\n"
            "- Cleaner for tree/graph traversal\n- Stack overhead O(depth)\n- Use `@lru_cache` for memoisation\n\n"
            "```python\nfrom functools import lru_cache\n\n@lru_cache(maxsize=None)\ndef fib(n): return n if n < 2 else fib(n-1) + fib(n-2)\n```\n"
            "Tail-call recursion is NOT optimised in CPython; refactor to iteration if depth > 1000."
        ),
    },
    "api": {
        "beginner": (
            "**API** stands for *Application Programming Interface* — it's a way for apps to talk to each other.\n\n"
            "Think of it like a restaurant menu 🍽️:\n"
            "- You (the app) place an order (request)\n"
            "- The kitchen (server) prepares it\n"
            "- The waiter (API) delivers the response\n\n"
            "```python\nimport requests\nresponse = requests.get('https://api.example.com/data')\nprint(response.json())\n```"
        ),
        "intermediate": (
            "**REST APIs** use HTTP methods: GET, POST, PUT, DELETE.\n\n"
            "Authentication is usually via API keys or OAuth tokens.\n"
            "Responses are typically JSON.\n\n"
            "```python\nimport httpx\n\nasync def fetch_user(user_id: int):\n    async with httpx.AsyncClient() as client:\n        r = await client.get(\n            f'https://api.example.com/users/{user_id}',\n            headers={'Authorization': 'Bearer TOKEN'}\n        )\n        r.raise_for_status()\n        return r.json()\n```"
        ),
        "advanced": (
            "**API Design** — key principles:\n\n"
            "| Concern | Best Practice |\n|---|---|\n| Versioning | `/v1/`, `/v2/` prefix |\n| Auth | OAuth 2.0 / JWT |\n| Rate Limiting | `429 Too Many Requests` + `Retry-After` header |\n| Errors | RFC 7807 Problem Details |\n| Pagination | Cursor-based for large sets |\n\n"
            "Use `FastAPI` + Pydantic for type-safe APIs with auto OpenAPI docs."
        ),
    },
}


class LearningAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="LearningAdvisor",
            skill="learn",
            description="Adapts explanations to your knowledge level — from beginner to expert",
            emoji="🎓",
        )

    # ── Level detection ───────────────────────────────────────────────────────

    @staticmethod
    def _detect_level(message: str) -> str:
        lower = message.lower()
        if any(w in lower for w in ["what is", "explain to me", "i don't understand",
                                    "eli5", "simple", "basic", "beginner", "newbie", "never"]):
            return "beginner"
        if any(w in lower for w in ["deep dive", "advanced", "internals", "under the hood",
                                    "performance", "complexity", "tradeoff", "how exactly"]):
            return "advanced"
        return "intermediate"

    @staticmethod
    def _detect_topic(message: str) -> Optional[str]:
        lower = message.lower()
        for topic in _KNOWLEDGE_BASE:
            if topic in lower:
                return topic
        return None

    # ── Fallback ──────────────────────────────────────────────────────────────

    @staticmethod
    def _generic_fallback(message: str, level: str) -> str:
        level_desc = {
            "beginner": "simple analogies and real-world examples",
            "intermediate": "practical code examples and design rationale",
            "advanced": "deep-dive internals, performance trade-offs, and production patterns",
        }[level]
        return (
            f"**🎓 Learning Mode — {level.capitalize()} Level**\n\n"
            f"I'll explain concepts using {level_desc}.\n\n"
            "**Topics I can teach:**\n"
            "- Programming concepts (recursion, OOP, async/await, closures)\n"
            "- Data structures & algorithms\n"
            "- System design patterns\n"
            "- APIs & web architecture\n"
            "- Machine learning fundamentals\n\n"
            "**Try:** *Explain recursion to me* or *Give me an advanced explanation of async I/O*"
        )

    # ── Main entry point ──────────────────────────────────────────────────────

    async def process(self, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        tools_used: List[str] = []
        level = self._detect_level(message)
        topic = self._detect_topic(message)

        # Try offline knowledge base first
        if topic and topic in _KNOWLEDGE_BASE:
            content = _KNOWLEDGE_BASE[topic][level]
            tools_used.append("knowledge_base")
        else:
            # LLM with adaptive prompt
            level_instructions = {
                "beginner": (
                    "Explain using simple language, real-world analogies, and short code examples. "
                    "Avoid jargon. Assume zero prior knowledge."
                ),
                "intermediate": (
                    "Explain with code examples, practical use cases, and common pitfalls. "
                    "Assume basic programming knowledge."
                ),
                "advanced": (
                    "Give an in-depth technical explanation covering internals, performance "
                    "trade-offs, design patterns, and production considerations. "
                    "Assume expert-level knowledge."
                ),
            }[level]

            content = self._generic_fallback(message, level)
            tools_used.append("fallback_engine")

        return AgentResponse(
            content=content,
            agent_name=self.name,
            skill=self.skill,
            tools_used=tools_used,
            metadata={"level": level, "topic": topic},
        )
