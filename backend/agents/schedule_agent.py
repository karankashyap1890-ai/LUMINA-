"""
Lumina Agent — Scheduler
Creates and lists reminders using SQLite (aiosqlite).
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiosqlite

from backend.agents.base_agent import BaseAgent, AgentResponse
from config.settings import settings


class ScheduleAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Scheduler",
            skill="schedule",
            description="Creates reminders and manages a personal task schedule",
            emoji="📅",
        )
        self._db_ready = False

    # ── DB init ───────────────────────────────────────────────────────────────

    async def _ensure_db(self) -> None:
        if self._db_ready:
            return
        os.makedirs(os.path.dirname(settings.db_path), exist_ok=True)
        async with aiosqlite.connect(settings.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    title       TEXT    NOT NULL,
                    description TEXT,
                    remind_at   TEXT,
                    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                    completed   INTEGER NOT NULL DEFAULT 0
                )
            """)
            await db.commit()
        self._db_ready = True

    # ── DB operations ─────────────────────────────────────────────────────────

    async def _create_reminder(self, title: str, description: str = "", remind_at: str = "") -> int:
        await self._ensure_db()
        async with aiosqlite.connect(settings.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO reminders (title, description, remind_at) VALUES (?,?,?)",
                (title, description, remind_at),
            )
            await db.commit()
            return cursor.lastrowid  # type: ignore[return-value]

    async def get_all_reminders(self) -> List[Dict[str, Any]]:
        await self._ensure_db()
        async with aiosqlite.connect(settings.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM reminders WHERE completed=0 ORDER BY created_at DESC LIMIT 50"
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def _complete_reminder(self, reminder_id: int) -> bool:
        await self._ensure_db()
        async with aiosqlite.connect(settings.db_path) as db:
            await db.execute("UPDATE reminders SET completed=1 WHERE id=?", (reminder_id,))
            await db.commit()
        return True

    # ── NL time parser ────────────────────────────────────────────────────────

    @staticmethod
    def _parse_time_hint(text: str) -> str:
        """Very simple natural-language → ISO-ish datetime string."""
        now = datetime.now()
        lower = text.lower()
        if "tomorrow" in lower:
            dt = now + timedelta(days=1)
        elif "next week" in lower:
            dt = now + timedelta(weeks=1)
        elif "in an hour" in lower or "in 1 hour" in lower:
            dt = now + timedelta(hours=1)
        elif "tonight" in lower:
            dt = now.replace(hour=20, minute=0, second=0, microsecond=0)
        elif "this evening" in lower:
            dt = now.replace(hour=18, minute=0, second=0, microsecond=0)
        else:
            # Try to extract time like "at 3pm" or "at 15:00"
            m = re.search(r"at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", lower)
            if m:
                hour = int(m.group(1))
                minute = int(m.group(2) or 0)
                meridiem = m.group(3)
                if meridiem == "pm" and hour < 12:
                    hour += 12
                elif meridiem == "am" and hour == 12:
                    hour = 0
                dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if dt < now:
                    dt += timedelta(days=1)
            else:
                return ""
        return dt.strftime("%Y-%m-%d %H:%M")

    # ── Fallback ──────────────────────────────────────────────────────────────

    @staticmethod
    def _fallback() -> str:
        return (
            "**📅 Lumina Scheduler**\n\n"
            "I can:\n"
            "- **Create reminders** — e.g. *Remind me to call John tomorrow at 3pm*\n"
            "- **List reminders** — e.g. *Show my reminders*\n"
            "- **Mark as done** — e.g. *Complete reminder 2*\n\n"
            "Just tell me what you need!"
        )

    # ── Main entry point ──────────────────────────────────────────────────────

    async def process(self, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        tools_used: List[str] = []
        lower = message.lower()

        # List reminders
        if any(w in lower for w in ["list", "show", "what are my", "my reminders", "upcoming"]):
            reminders = await self.get_all_reminders()
            tools_used.append("list_reminders")
            if reminders:
                lines = ["### 📋 Your Upcoming Reminders\n"]
                for r in reminders:
                    when = f" — *{r['remind_at']}*" if r.get("remind_at") else ""
                    lines.append(f"**[{r['id']}]** {r['title']}{when}")
                    if r.get("description"):
                        lines.append(f"  _{r['description']}_")
                content = "\n".join(lines)
            else:
                content = "📭 No active reminders. Create one by telling me what to remind you about!"

        # Complete reminder
        elif "complete" in lower or "done" in lower or "finish" in lower:
            m = re.search(r"\b(\d+)\b", message)
            if m:
                rid = int(m.group(1))
                await self._complete_reminder(rid)
                tools_used.append("complete_reminder")
                content = f"✅ Reminder **#{rid}** marked as complete."
            else:
                content = "Please specify the reminder ID, e.g. *Complete reminder 3*"

        # Create reminder
        elif any(w in lower for w in ["remind", "schedule", "add task", "create", "set a reminder"]):
            # Regex heuristic: extract title and time hint from message
            m2 = re.search(r"remind(?:\s+me)?\s+(?:to\s+)?(.+?)(?:\s+(?:at|on|tomorrow|tonight|next).*)?$",
                            lower, re.IGNORECASE)
            title = m2.group(1).strip().capitalize() if m2 else message[:80]
            time_hint = message

            remind_at = self._parse_time_hint(time_hint)
            rid = await self._create_reminder(title, remind_at=remind_at)
            tools_used.append("create_reminder")
            when_str = f" for **{remind_at}**" if remind_at else ""
            content = (
                f"✅ Reminder **#{rid}** created{when_str}:\n"
                f"> 📌 {title}\n\n"
                "Use *show my reminders* to see all tasks."
            )

        else:
            # General scheduling question — use built-in advice
            content = self._fallback()
            tools_used.append("fallback_engine")

        return AgentResponse(
            content=content,
            agent_name=self.name,
            skill=self.skill,
            tools_used=tools_used,
        )
