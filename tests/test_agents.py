"""
Tests — Specialist Agents
Verifies each agent produces valid AgentResponse objects.
"""
import pytest
from backend.agents.base_agent import AgentResponse
from backend.agents.data_agent import DataAgent
from backend.agents.code_agent import CodeAgent
from backend.agents.schedule_agent import ScheduleAgent
from backend.agents.learning_agent import LearningAgent
from backend.agents.troubleshoot_agent import TroubleshootAgent
from backend.agents.orchestrator import Orchestrator


# ── Helper ───────────────────────────────────────────────────────────────────

def assert_valid_response(resp: AgentResponse):
    assert isinstance(resp, AgentResponse)
    assert isinstance(resp.content, str)
    assert len(resp.content) > 0
    assert isinstance(resp.tools_used, list)
    assert isinstance(resp.metadata, dict)


# ── Data agent ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_data_agent_general_question():
    agent = DataAgent()
    resp = await agent.process("What is the mean?")
    assert_valid_response(resp)
    assert resp.skill == "data"


@pytest.mark.asyncio
async def test_data_agent_csv_analysis():
    csv = "```csv\nname,age,score\nAlice,30,90\nBob,25,85\nCarol,35,95\n```"
    agent = DataAgent()
    resp = await agent.process(f"Analyse this data: {csv}")
    assert_valid_response(resp)
    assert "analyze_csv" in resp.tools_used
    assert resp.metadata.get("has_csv") is True


# ── Code agent ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_code_agent_general_question():
    agent = CodeAgent()
    resp = await agent.process("How do I use async/await?")
    assert_valid_response(resp)
    assert resp.skill == "code"


@pytest.mark.asyncio
async def test_code_agent_code_block():
    code_msg = "Review this:\n```python\ndef add(a, b):\n    return a + b\nprint(add(2,3))\n```"
    agent = CodeAgent()
    resp = await agent.process(code_msg)
    assert_valid_response(resp)
    assert "ast_reviewer" in resp.tools_used


# ── Schedule agent ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_schedule_agent_create(tmp_path, monkeypatch):
    # Redirect DB to temp location
    from config import settings as s_mod
    monkeypatch.setattr(s_mod.settings, "db_path", str(tmp_path / "test.db"))

    agent = ScheduleAgent()
    resp = await agent.process("Remind me to call Alice tomorrow")
    assert_valid_response(resp)
    assert "create_reminder" in resp.tools_used


@pytest.mark.asyncio
async def test_schedule_agent_list(tmp_path, monkeypatch):
    from config import settings as s_mod
    monkeypatch.setattr(s_mod.settings, "db_path", str(tmp_path / "test.db"))

    agent = ScheduleAgent()
    resp = await agent.process("Show my reminders")
    assert_valid_response(resp)
    assert "list_reminders" in resp.tools_used


# ── Learning agent ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_learning_agent_beginner():
    agent = LearningAgent()
    resp = await agent.process("Explain recursion to a beginner")
    assert_valid_response(resp)
    assert resp.skill == "learn"
    assert resp.metadata.get("level") == "beginner"


@pytest.mark.asyncio
async def test_learning_agent_advanced():
    agent = LearningAgent()
    resp = await agent.process("Give me an advanced explanation of recursion")
    assert resp.metadata.get("level") == "advanced"


@pytest.mark.asyncio
async def test_learning_agent_knowledge_base():
    agent = LearningAgent()
    resp = await agent.process("What is an API?")
    assert_valid_response(resp)


# ── Troubleshoot agent ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_troubleshoot_known_error():
    agent = TroubleshootAgent()
    resp = await agent.process("I'm getting a KeyError in my dictionary")
    assert_valid_response(resp)
    assert resp.metadata.get("matched_error") == "KeyError"


@pytest.mark.asyncio
async def test_troubleshoot_module_not_found():
    agent = TroubleshootAgent()
    resp = await agent.process("ModuleNotFoundError: No module named 'pandas'")
    assert_valid_response(resp)
    assert resp.metadata.get("matched_error") == "ModuleNotFoundError"


@pytest.mark.asyncio
async def test_troubleshoot_unknown_error():
    agent = TroubleshootAgent()
    resp = await agent.process("My app is suddenly very slow, not sure why")
    assert_valid_response(resp)


# ── Orchestrator ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_orchestrator_routes_data():
    orch = Orchestrator()
    resp = await orch.route("Analyze this CSV data", skill="auto")
    assert resp.skill == "data"


@pytest.mark.asyncio
async def test_orchestrator_routes_code():
    orch = Orchestrator()
    resp = await orch.route("Help me debug this Python function", skill="auto")
    assert resp.skill == "code"


@pytest.mark.asyncio
async def test_orchestrator_explicit_skill():
    orch = Orchestrator()
    resp = await orch.route("hello world", skill="learn")
    assert resp.skill == "learn"


@pytest.mark.asyncio
async def test_orchestrator_handles_exception_gracefully():
    orch = Orchestrator()
    # Pass an empty message that might cause edge cases
    resp = await orch.route("", skill="auto")
    assert isinstance(resp, AgentResponse)
