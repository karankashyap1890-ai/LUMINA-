# Lumina — Antigravity Demo
## End-to-End Workflow Walkthrough

> This document demonstrates the complete Lumina AI Agent System workflow from boot to conversation.

---

## 🚀 Phase 1 — Boot Sequence

### Step 1: Start the server

```bash
cd c:\Users\karan\OneDrive\Lumina
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Expected console output:**
```
00:01:02 | INFO     | lumina.api — ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
00:01:02 | INFO     | lumina.api — 🌟  LUMINA AI AGENT SYSTEM — STARTING UP
00:01:02 | INFO     | lumina.api — ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
00:01:02 | INFO     | lumina.agent.dataanalyst — LLM unavailable (fallback mode active)
00:01:02 | INFO     | lumina.agent.codeassistant — LLM unavailable (fallback mode active)
00:01:02 | INFO     | lumina.agent.scheduler — LLM unavailable (fallback mode active)
00:01:02 | INFO     | lumina.agent.learningadvisor — LLM unavailable (fallback mode active)
00:01:02 | INFO     | lumina.agent.troubleshooter — LLM unavailable (fallback mode active)
00:01:02 | INFO     | lumina.orchestrator — Orchestrator initialised with 5 agents
00:01:02 | INFO     | lumina.api — 🔌  MCP Server launching on port 8001 ...
00:01:02 | INFO     | lumina.mcp — ✅ MCP Server running at http://0.0.0.0:8001 — 10 tools registered
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Step 2: Verify health

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "app": "Lumina AI Agent System",
  "version": "1.0.0",
  "ai_enabled": false,
  "agents": [
    {"name": "DataAnalyst",      "skill": "data",         "emoji": "📊", "ai_enabled": false},
    {"name": "CodeAssistant",    "skill": "code",         "emoji": "💻", "ai_enabled": false},
    {"name": "Scheduler",        "skill": "schedule",     "emoji": "📅", "ai_enabled": false},
    {"name": "LearningAdvisor",  "skill": "learn",        "emoji": "🎓", "ai_enabled": false},
    {"name": "Troubleshooter",   "skill": "troubleshoot", "emoji": "🔧", "ai_enabled": false}
  ],
  "mcp_url": "http://localhost:8001"
}
```

---

## 💬 Phase 2 — Chat Flows

### Flow A: Auto-detect → Learning Agent

**Request:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is recursion? Explain simply.", "skill": "auto"}'
```

**Orchestrator routing:** 
- Scores: `learn: 3` (what is, explain, simply) > others → routes to **LearningAgent**
- Level detection: "simply" → **beginner**
- Topic detection: *(no match in KB, uses LLM or fallback)*

**Response:**
```json
{
  "content": "**Recursion** means a function calls *itself*...\n```python\ndef countdown(n):\n...\n```",
  "agent_name": "LearningAdvisor",
  "skill": "learn",
  "tools_used": ["knowledge_base"],
  "metadata": {"level": "beginner", "topic": "recursion"},
  "confidence": 1.0
}
```

---

### Flow B: Code Execution Through Sandbox

**Request:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Run this code:\n```python\nfor i in range(5):\n    print(i**2)\n```",
    "skill": "code"
  }'
```

**Orchestrator routing:** Explicit `skill: "code"` → **CodeAgent**

**Internal flow:**
1. `_extract_code_block()` → extracts Python snippet
2. `_ast_review()` → ✅ No issues
3. `execute_code_safely()`:
   - Stage 1: AST validation passes
   - Stage 2: Subprocess runs `python -u /tmp/sandbox_xxx.py`
   - Output: `0\n1\n4\n9\n16`
   - Temp file deleted

**Response:**
```json
{
  "content": "### 🔍 Static Analysis\n- ✅ No obvious issues\n\n### ✅ Execution Output (0.12s)\n```\n0\n1\n4\n9\n16\n```",
  "agent_name": "CodeAssistant",
  "skill": "code",
  "tools_used": ["ast_reviewer", "sandbox_executor"]
}
```

---

### Flow C: Security Block

**Request:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Run this:\n```python\nimport os\nos.system(\"dir\")\n```",
    "skill": "code"
  }'
```

**Security flow:**
1. `validate_ast()` → detects `import os`
2. Raises `SecurityError("Import of 'os' is blocked in sandbox")`
3. Returns blocked response immediately (subprocess never called)

**Response:**
```json
{
  "content": "### 🔍 Static Analysis\n- ...\n\n### 🔒 Security\n🔒 Security block: Import of 'os' is blocked in sandbox",
  "agent_name": "CodeAssistant",
  "skill": "code",
  "tools_used": ["ast_reviewer", "sandbox_executor"],
  "metadata": {"has_code": true}
}
```

---

### Flow D: CSV Data Analysis

**Request:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Analyse this:\n```csv\nproduct,sales,price\nWidget A,150,29.99\nWidget B,89,49.99\nWidget C,210,19.99\n```",
    "skill": "data"
  }'
```

**Internal flow:**
1. `_extract_csv()` → finds CSV block
2. `_analyse_csv()` via pandas:
   - Shape: 3 rows × 3 columns
   - Numeric: `sales`, `price`
   - Stats: mean sales=149.67, mean price=33.32
   - Correlation: sales ↔ price = -0.94

**Response:**
```json
{
  "content": "### 📊 Dataset Overview\n- **Rows:** 3 | **Columns:** 3\n...\n### 🔗 Strongest Correlation\n  **sales** ↔ **price** — r = -0.94",
  "agent_name": "DataAnalyst",
  "skill": "data",
  "tools_used": ["analyze_csv"],
  "metadata": {"has_csv": true}
}
```

---

### Flow E: Scheduling a Reminder

**Request:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Remind me to submit my report tomorrow at 5pm", "skill": "schedule"}'
```

**Internal flow:**
1. Detects "remind" keyword → create path
2. `_parse_time_hint("tomorrow at 5pm")` → `"2026-06-28 17:00"`
3. `_create_reminder("Submit my report", remind_at="2026-06-28 17:00")` → INSERT into SQLite
4. Returns ID `#1`

**Response:**
```json
{
  "content": "✅ Reminder **#1** created for **2026-06-28 17:00**:\n> 📌 Submit my report\n\nUse *show my reminders* to see all tasks.",
  "agent_name": "Scheduler",
  "skill": "schedule",
  "tools_used": ["create_reminder"]
}
```

---

### Flow F: Error Troubleshooting

**Request:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I keep getting KeyError: name in my user dict", "skill": "troubleshoot"}'
```

**Internal flow:**
1. `_match_error("KeyError")` → found in `_ERROR_PATTERNS`
2. Returns structured cause + 3-step fix
3. Optional LLM supplement

**Response:**
```json
{
  "content": "### 🔴 Error Detected: `KeyError`\n\n**Root Cause:** You're accessing a dictionary key that doesn't exist.\n\n**Resolution Steps:**\n1. Use `.get(key, default)` instead of `dict[key]`\n...",
  "agent_name": "Troubleshooter",
  "skill": "troubleshoot",
  "tools_used": ["error_pattern_db"],
  "metadata": {"matched_error": "KeyError"}
}
```

---

## 🔌 Phase 3 — MCP Server Workflow

### Tool listing

```bash
curl -X POST http://localhost:8001/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"list_tools","params":{},"id":1}'
```

```json
{
  "jsonrpc": "2.0",
  "result": {
    "tools": [
      {"name": "run_code",         "description": "Execute a Python snippet..."},
      {"name": "format_code",      "description": "Format Python code..."},
      {"name": "explain_error",    "description": "Given a Python error..."},
      {"name": "analyze_csv",      "description": "Parse CSV text..."},
      {"name": "generate_chart_spec", "description": "Generate a Chart.js spec..."},
      {"name": "create_reminder",  "description": "Create a new reminder..."},
      {"name": "list_reminders",   "description": "List all active reminders"},
      {"name": "complete_reminder","description": "Mark a reminder as completed"},
      {"name": "explain_concept",  "description": "Explain a programming concept..."},
      {"name": "lookup_error",     "description": "Look up a Python exception..."},
      {"name": "system_status",    "description": "Return current Lumina health"}
    ]
  },
  "id": 1
}
```

### Safe code execution via MCP

```bash
curl -X POST http://localhost:8001/rpc \
  -d '{"jsonrpc":"2.0","method":"run_code","params":{"code":"import math\nprint(f\"Pi = {math.pi:.5f}\")"},"id":2}'
```

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "output": "Pi = 3.14159\n",
    "error": "",
    "execution_time": 0.087,
    "security_blocked": false
  },
  "id": 2
}
```

### MCP error response (method not found)

```bash
curl -X POST http://localhost:8001/rpc \
  -d '{"jsonrpc":"2.0","method":"unknown_tool","params":{},"id":99}'
```

```json
{
  "jsonrpc": "2.0",
  "error": {"code": -32601, "message": "Method 'unknown_tool' not found"},
  "id": 99
}
```

---

## 🛠️ Phase 4 — CLI Workflow

```bash
# 1. Check system status
python -m backend.cli.lumina_cli status

╭─────────────── Lumina System Status ───────────────╮
│ Status   │ ok                                      │
│ Version  │ 1.0.0                                   │
│ AI       │ ⚠️  No (fallback mode)                  │
│ MCP      │ http://localhost:8001                   │
╰────────────────────────────────────────────────────╯

# 2. Interactive chat
python -m backend.cli.lumina_cli chat --skill learn
You: Explain recursion to a beginner
🤖 LearningAdvisor (learn)
[Recursion explanation with examples...]

# 3. Analyse CSV
python -m backend.cli.lumina_cli analyze sales_data.csv

# 4. Create reminder
python -m backend.cli.lumina_cli schedule --add "Review pull requests"

# 5. List reminders
python -m backend.cli.lumina_cli schedule --list
```

---

## 🌐 Phase 5 — Frontend UI Workflow

1. Open `http://localhost:8000` in browser
2. Glassmorphic UI loads with animated gradient background
3. Welcome card shows 5 skill cards
4. WebSocket connects automatically (green status dot)
5. Select skill from sidebar or click welcome card
6. Type message and press Enter
7. Typing indicator appears while agent processes
8. Response renders with:
   - Agent name + skill badge
   - Markdown-formatted content (headers, code blocks, tables)
   - Tools used chips at bottom
9. Try quick prompts in sidebar for instant demo

---

## 📊 System Performance

| Metric | Value |
|---|---|
| Server boot time | ~2 seconds |
| Agent response (fallback) | <50ms |
| Code sandbox execution | <1 second (simple) |
| Sandbox timeout | 10 seconds (configurable) |
| Rate limit | 60 req/min/IP |
| Max message length | 10,000 chars |

---

## ✅ Verification Checklist

- [ ] `uvicorn backend.main:app` boots without errors
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] MCP server starts on port 8001
- [ ] Frontend loads at `http://localhost:8000`
- [ ] WebSocket connects (green dot in UI)
- [ ] Chat with each of 5 skills returns responses
- [ ] Code sandbox blocks `import os`
- [ ] Code sandbox executes `print("hello")` successfully
- [ ] Reminder is created and appears in `/api/reminders`
- [ ] Rate limiter triggers after 60 rapid requests
- [ ] JWT token grants access to protected endpoints
- [ ] `python -m backend.cli.lumina_cli status` shows agent list
- [ ] All 41 tests pass with `pytest tests/ -v`
