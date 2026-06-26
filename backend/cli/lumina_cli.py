"""
Lumina CLI — Command-Line Interface
A rich, interactive terminal client for the Lumina AI Agent System.

Usage:
    python -m backend.cli.lumina_cli [COMMAND] [OPTIONS]

Commands:
    chat          Interactive chat with skill selection
    analyze       Analyse a CSV file
    schedule      Manage reminders
    debug         Debug code or error messages
    learn         Explain a concept
    status        Show system status
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import click
import httpx

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.table import Table
    from rich import print as rprint
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

API_BASE = "http://localhost:8000"
console = Console() if HAS_RICH else None


def _print(text: str, style: str = ""):
    if HAS_RICH and console:
        console.print(text, style=style)
    else:
        print(text)


def _render_response(data: dict):
    content = data.get("content", "")
    agent = data.get("agent_name", "Lumina")
    skill = data.get("skill", "")
    tools = data.get("tools_used", [])

    if HAS_RICH and console:
        console.print(f"\n[bold cyan]🤖 {agent}[/bold cyan] [dim]({skill})[/dim]")
        console.print(Markdown(content))
        if tools:
            console.print(f"[dim]Tools: {', '.join(tools)}[/dim]\n")
    else:
        print(f"\n[{agent} | {skill}]\n{content}")
        if tools:
            print(f"(tools: {', '.join(tools)})\n")


async def _post(endpoint: str, payload: dict) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{API_BASE}{endpoint}", json=payload)
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        _print("❌  Cannot connect to Lumina API. Is the server running?", style="red")
        _print(f"   Start it with: uvicorn backend.main:app --port 8000", style="dim")
        return None
    except httpx.HTTPStatusError as exc:
        _print(f"❌  API error {exc.response.status_code}: {exc.response.text}", style="red")
        return None


async def _get(endpoint: str) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{API_BASE}{endpoint}")
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        _print(f"❌  {exc}", style="red")
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI Group
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@click.group()
@click.version_option("1.0.0", prog_name="lumina")
def cli():
    """🌟 Lumina AI Agent System — Command Line Interface"""


# ── status ─────────────────────────────────────────────────────────────────────

@cli.command()
def status():
    """Show system health and agent status."""
    async def _run():
        data = await _get("/health")
        if not data:
            return
        if HAS_RICH and console:
            table = Table(title="Lumina System Status", show_header=True, header_style="bold cyan")
            table.add_column("Component", style="bold")
            table.add_column("Value")
            table.add_row("Status",      f"[green]{data['status']}[/green]")
            table.add_row("Version",     data.get("version", "?"))
            table.add_row("AI Enabled",  "✅ Yes" if data.get("ai_enabled") else "⚠️  No (fallback mode)")
            table.add_row("MCP Server",  data.get("mcp_url", "?"))
            console.print(table)

            agents = data.get("agents", [])
            if agents:
                a_table = Table(title="Specialist Agents", show_header=True, header_style="bold magenta")
                a_table.add_column("Name")
                a_table.add_column("Skill")
                a_table.add_column("AI")
                for a in agents:
                    a_table.add_row(
                        f"{a.get('emoji','')} {a['name']}",
                        a["skill"],
                        "✅" if a.get("ai_enabled") else "⚠️",
                    )
                console.print(a_table)
        else:
            print(json.dumps(data, indent=2))

    asyncio.run(_run())


# ── chat ───────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--skill", "-s", default="auto",
              type=click.Choice(["auto", "data", "code", "schedule", "learn", "troubleshoot"]),
              help="Force a specific skill (default: auto-detect)")
def chat(skill: str):
    """Start an interactive chat session with Lumina."""
    _print("\n🌟 Lumina Interactive Chat", style="bold cyan")
    _print(f"   Skill: [bold]{skill}[/bold]  |  Type 'exit' to quit\n", style="dim")

    async def _run():
        while True:
            try:
                if HAS_RICH and console:
                    message = Prompt.ask("[bold green]You[/bold green]")
                else:
                    message = input("You: ")
            except (KeyboardInterrupt, EOFError):
                _print("\nGoodbye! 👋", style="cyan")
                break

            if message.strip().lower() in ("exit", "quit", "bye"):
                _print("Goodbye! 👋", style="cyan")
                break

            data = await _post("/api/chat", {"message": message, "skill": skill})
            if data:
                _render_response(data)

    asyncio.run(_run())


# ── analyze ────────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("file", type=click.Path(exists=True))
def analyze(file: str):
    """Analyse a CSV file using the Data Analysis agent."""
    path = Path(file)
    _print(f"\n📊 Analysing [bold]{path.name}[/bold]...\n", style="cyan")

    async def _run():
        csv_text = path.read_text(encoding="utf-8")
        message = f"Analyse this CSV data:\n```csv\n{csv_text[:5000]}\n```"
        data = await _post("/api/chat", {"message": message, "skill": "data"})
        if data:
            _render_response(data)

    asyncio.run(_run())


# ── debug ──────────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("error_or_file", required=False)
def debug(error_or_file: Optional[str]):
    """Debug a Python error or code file."""
    if error_or_file and Path(error_or_file).exists():
        code = Path(error_or_file).read_text()
        message = f"Review and debug this code:\n```python\n{code}\n```"
    elif error_or_file:
        message = f"Help me fix this error:\n```\n{error_or_file}\n```"
    else:
        if HAS_RICH and console:
            message = Prompt.ask("Paste your error or code")
        else:
            message = input("Paste your error or code: ")

    async def _run():
        data = await _post("/api/chat", {"message": message, "skill": "code"})
        if data:
            _render_response(data)

    asyncio.run(_run())


# ── learn ──────────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("topic")
@click.option("--level", "-l", default="intermediate",
              type=click.Choice(["beginner", "intermediate", "advanced"]))
def learn(topic: str, level: str):
    """Explain a concept at a given knowledge level."""
    message = f"Explain {topic} at {level} level"
    _print(f"\n🎓 Learning: [bold]{topic}[/bold] [{level}]\n", style="magenta")

    async def _run():
        data = await _post("/api/chat", {"message": message, "skill": "learn"})
        if data:
            _render_response(data)

    asyncio.run(_run())


# ── schedule ───────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--add", "-a", "title", help="Add a new reminder")
@click.option("--list", "-l", "do_list", is_flag=True, help="List all reminders")
@click.option("--complete", "-c", "rem_id", type=int, help="Mark reminder ID as done")
def schedule(title: Optional[str], do_list: bool, rem_id: Optional[int]):
    """Manage reminders and scheduled tasks."""
    async def _run():
        if do_list:
            data = await _get("/api/reminders")
            if data:
                reminders = data.get("reminders", [])
                if HAS_RICH and console:
                    table = Table(title="Active Reminders", show_header=True, header_style="bold cyan")
                    table.add_column("ID", style="dim")
                    table.add_column("Title", style="bold")
                    table.add_column("When")
                    for r in reminders:
                        table.add_row(str(r["id"]), r["title"], r.get("remind_at", "—"))
                    console.print(table)
                else:
                    for r in reminders:
                        print(f"[{r['id']}] {r['title']} — {r.get('remind_at','')}")
                if not reminders:
                    _print("No active reminders.", style="dim")
        elif title:
            data = await _post("/api/chat", {"message": f"Remind me to {title}", "skill": "schedule"})
            if data:
                _render_response(data)
        elif rem_id is not None:
            data = await _post("/api/chat", {"message": f"Complete reminder {rem_id}", "skill": "schedule"})
            if data:
                _render_response(data)
        else:
            _print("Use --add, --list, or --complete. Run `lumina schedule --help`", style="yellow")

    asyncio.run(_run())


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cli()
