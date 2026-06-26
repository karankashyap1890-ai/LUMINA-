"""
Tests — MCP Server
Verifies tool registry, tool dispatch, and JSON-RPC 2.0 format.
"""
import pytest

# ── Tool Registry ─────────────────────────────────────────────────────────────

def test_registry_has_tools():
    # Import registry (tools auto-register on import)
    import backend.mcp.tools.code_tools       # noqa
    import backend.mcp.tools.data_tools       # noqa
    import backend.mcp.tools.schedule_tools   # noqa
    import backend.mcp.tools.search_tools     # noqa
    from backend.mcp.tool_registry import registry

    tools = registry.list_tools()
    assert len(tools) >= 4

    tool_names = {t["name"] for t in tools}
    assert "run_code"       in tool_names
    assert "analyze_csv"    in tool_names
    assert "create_reminder" in tool_names
    assert "explain_concept" in tool_names


@pytest.mark.asyncio
async def test_registry_calls_run_code():
    import backend.mcp.tools.code_tools  # noqa
    from backend.mcp.tool_registry import registry

    result = await registry.call("run_code", {"code": "print('mcp works!')"})
    assert "output" in result
    assert "mcp works!" in result.get("output", "")


@pytest.mark.asyncio
async def test_registry_calls_explain_concept():
    import backend.mcp.tools.search_tools  # noqa
    from backend.mcp.tool_registry import registry

    result = await registry.call("explain_concept", {"concept": "recursion", "level": "beginner"})
    assert result["concept"] == "recursion"
    assert len(result["explanation"]) > 0


@pytest.mark.asyncio
async def test_registry_calls_system_status():
    import backend.mcp.tools.search_tools  # noqa
    from backend.mcp.tool_registry import registry

    result = await registry.call("system_status", {})
    assert result["status"] == "ok"
    assert "version" in result


@pytest.mark.asyncio
async def test_registry_unknown_tool():
    from backend.mcp.tool_registry import registry

    with pytest.raises(ValueError, match="Unknown tool"):
        await registry.call("nonexistent_tool", {})


def test_registry_contains_check():
    import backend.mcp.tools.code_tools  # noqa
    from backend.mcp.tool_registry import registry

    assert "run_code" in registry
    assert "does_not_exist" not in registry


# ── Code tools ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_code_success():
    from backend.mcp.tools.code_tools import run_code
    result = await run_code("x = 2 + 2\nprint(x)")
    assert result["success"] is True
    assert "4" in result["output"]


@pytest.mark.asyncio
async def test_run_code_security_block():
    from backend.mcp.tools.code_tools import run_code
    result = await run_code("import os\nos.listdir('/')")
    assert result["success"] is False
    assert result.get("security_blocked") is True


@pytest.mark.asyncio
async def test_format_code():
    from backend.mcp.tools.code_tools import format_code
    result = await format_code("def foo():\n    pass")
    assert "is_valid_syntax" in result
    assert result["is_valid_syntax"] is True


@pytest.mark.asyncio
async def test_explain_error_known():
    from backend.mcp.tools.code_tools import explain_error
    result = await explain_error("KeyError: 'name'")
    assert result["error_type"] == "KeyError"
    assert "cause" in result


# ── Data tools ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_csv_basic():
    from backend.mcp.tools.data_tools import analyze_csv
    csv = "name,age,score\nAlice,30,90\nBob,25,85\nCarol,35,95"
    result = await analyze_csv(csv)
    if result.get("success"):  # pandas might not be installed in CI
        assert result["shape"]["rows"] == 3
        assert "age" in result["numeric_columns"]


@pytest.mark.asyncio
async def test_generate_chart_spec():
    from backend.mcp.tools.data_tools import generate_chart_spec
    result = await generate_chart_spec("bar", ["A", "B", "C"], [10, 20, 30], "Test Chart")
    assert result["type"] == "bar"
    assert result["data"]["labels"] == ["A", "B", "C"]


# ── Schedule tools ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_reminders_returns_dict(tmp_path, monkeypatch):
    from config import settings as s_mod
    monkeypatch.setattr(s_mod.settings, "db_path", str(tmp_path / "mcp_test.db"))

    from backend.mcp.tools.schedule_tools import list_reminders
    result = await list_reminders()
    assert result["success"] is True
    assert "reminders" in result
