"""
Lumina MCP Tools — Schedule Tools
Reminder CRUD operations exposed over MCP.
"""
from __future__ import annotations

from typing import Any, Dict, List

from backend.mcp.tool_registry import registry


@registry.register(
    name="create_reminder",
    description="Create a new reminder in the Lumina scheduler database.",
    parameters={
        "type": "object",
        "properties": {
            "title":       {"type": "string",  "description": "Short reminder title"},
            "description": {"type": "string",  "description": "Optional detail"},
            "remind_at":   {"type": "string",  "description": "ISO date-time string (optional)"},
        },
        "required": ["title"],
    },
)
async def create_reminder(title: str, description: str = "", remind_at: str = "") -> Dict[str, Any]:
    """Delegate to the ScheduleAgent's DB layer."""
    # Late import to avoid circular dependency at module load time
    from backend.agents.schedule_agent import ScheduleAgent
    agent = ScheduleAgent()
    rid = await agent._create_reminder(title, description, remind_at)
    return {"success": True, "id": rid, "title": title, "remind_at": remind_at}


@registry.register(
    name="list_reminders",
    description="List all active (not completed) reminders.",
    parameters={"type": "object", "properties": {}, "required": []},
)
async def list_reminders() -> Dict[str, Any]:
    from backend.agents.schedule_agent import ScheduleAgent
    agent = ScheduleAgent()
    rows = await agent.get_all_reminders()
    return {"success": True, "count": len(rows), "reminders": rows}


@registry.register(
    name="complete_reminder",
    description="Mark a reminder as completed by its ID.",
    parameters={
        "type": "object",
        "properties": {
            "reminder_id": {"type": "integer", "description": "The reminder ID to mark done"},
        },
        "required": ["reminder_id"],
    },
)
async def complete_reminder(reminder_id: int) -> Dict[str, Any]:
    from backend.agents.schedule_agent import ScheduleAgent
    agent = ScheduleAgent()
    await agent._complete_reminder(reminder_id)
    return {"success": True, "completed_id": reminder_id}
