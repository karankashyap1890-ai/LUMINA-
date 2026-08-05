# ✦ Lumina — Full-Stack AI Agent System

<div align="center">

![Lumina Banner](https://img.shields.io/badge/Lumina-AI%20Agent%20System-6366f1?style=for-the-badge&logo=lightning&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![MCP](https://img.shields.io/badge/MCP-JSON--RPC%202.0-22d3ee?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**Lumina is a locally runnable AI agent platform that combines a FastAPI backend, web UI, MCP tool server, JWT security, and five specialist agents. It works offline without external API keys, so you can deploy and test it on your machine with minimal setup.**

[🚀 Quick Start](#-quick-start) · [🏗️ Architecture](#️-architecture) · [🔐 Security](#-security) · [🔌 MCP Server](#-mcp-server) · [🛠️ CLI](#️-cli-tools) · [📖 API Docs](#-api-reference)

</div>

---

## 📋 Table of Contents

- [Features](#-features)
- [Key Concepts](#-key-concepts)
- [Quick Start](#-quick-start)
- [Architecture](#️-architecture)
- [Agent Skills](#-agent-skills)
- [MCP Server](#-mcp-server)
- [Security](#-security)
- [CLI Tools](#️-cli-tools)
- [API Reference](#-api-reference)
- [Configuration](#️-configuration)
- [Docker Deployment](#-docker-deployment)
- [Running Tests](#-running-tests)
- [Project Structure](#-project-structure)

---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 **5 Specialist Agents** | Data Analysis · Code Assistant · Scheduler · Learning · Troubleshooter |
| 🧠 **Self-Contained AI** | Built-in knowledge bases, AST analysis, pattern matching — **zero external API keys needed** |
| 🔌 **MCP Server** | JSON-RPC 2.0 tool server on port 8001 with 8 registered tools |
| 🔐 **Security** | Pydantic validation · JWT auth · Rate limiting · AST sandbox |
| 🛠️ **CLI** | Rich terminal client with 6 commands (`chat`, `analyze`, `debug`, `learn`, `schedule`, `status`) |
| 💎 **Premium UI** | Glassmorphic dark mode, WebSocket chat, skill selector, markdown rendering |
| 🐳 **Docker Ready** | Single `docker compose up` deploys everything |
| 🧪 **30+ Tests** | Security, agent, and MCP tests with pytest-asyncio |

---

## 🎯 Key Concepts

This project demonstrates **4 core engineering concepts**:

### 1. 🤖 ADK Multi-Agent System
An orchestrator agent routes messages to 5 specialist agents using keyword-scoring intent detection. Each agent is independently testable and follows a common `BaseAgent` interface.

```
User Message → Orchestrator → Intent Detection → Specialist Agent → AgentResponse
```

### 2. 🔌 MCP Server (Model Context Protocol)
A custom JSON-RPC 2.0 server running on port 8001, exposing 8 tools:

```json
POST http://localhost:8001/rpc
{"jsonrpc": "2.0", "method": "run_code", "params": {"code": "print('hello')"}, "id": 1}
```

### 3. 🔐 Security (Validation + Safe Execution)
- **Input validation**: Pydantic v2 models strip HTML, block null bytes, enforce length limits
- **AST sandbox**: Two-stage code validation (static AST analysis + subprocess isolation)
- **JWT auth**: HS256 tokens with optional auth (guest mode available)
- **Rate limiting**: Sliding-window per-IP rate limiter (60 req/min default)

### 4. 🛠️ Agent Skills / CLI Tools
Each agent exposes its capability as a discrete `skill`. The CLI wraps these skills with a rich terminal interface, and the MCP server exposes them as callable JSON-RPC tools.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- pip

### 1. Clone & setup

```bash
git clone https://github.com/yourname/lumina.git
cd lumina

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# No API key needed — Lumina runs fully self-contained
```

### 3. Start the server

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Open the UI

```
http://localhost:8000
```

### 5. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Chat
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain recursion to a beginner", "skill": "learn"}'

# MCP tool call
curl -X POST http://localhost:8001/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"run_code","params":{"code":"print(2**10)"},"id":1}'
```

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    LUMINA FRONTEND (Port 8000/)                  │
│         Glassmorphic UI  ·  WebSocket Chat  ·  Skill Selector    │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTP / WebSocket
┌────────────────────────────▼─────────────────────────────────────┐
│                  FASTAPI BACKEND  (Port 8000)                    │
│   CORS → Auth Middleware → Rate Limiter → Input Validator        │
│                                                                  │
│   GET  /health          POST /api/chat       GET /api/agents     │
│   POST /api/token       POST /api/execute    GET /api/reminders  │
│   POST /api/mcp         WS   /ws/{session}                       │
└────────┬────────────────────────────────────────────┬────────────┘
         │                                            │
┌────────▼────────┐                        ┌──────────▼────────────┐
│   ORCHESTRATOR  │                        │    MCP SERVER          │
│   (ADK Router)  │◄──── tool calls ───────│  JSON-RPC 2.0          │
│                 │                        │  Port 8001             │
│  Intent Scoring │                        │  8 Tools registered    │
└────────┬────────┘                        └───────────────────────┘
         │ routes to
┌────────▼──────────────────────────────────────────────────────┐
│                    SPECIALIST AGENTS                          │
│                                                               │
│  📊 DataAgent      💻 CodeAgent      📅 ScheduleAgent        │
│  🎓 LearningAgent  🔧 TroubleshootAgent                      │
│                                                               │
│  Each: Built-in Engine → AgentResponse                       │
└────────────────────────────────────────────────────────────┬──┘
                                                             │
┌────────────────────────────────────────────────────────────▼──┐
│                    SECURITY LAYER                             │
│  validator.py  ·  sandbox.py  ·  auth.py  ·  rate_limiter.py │
└───────────────────────────────────────────────────────────────┘
```

---

## 🤖 Agent Skills

### 📊 Data Analysis Agent
- Detects and parses CSV blocks from messages
- Computes descriptive statistics (mean, std, quartiles) via pandas
- Finds top correlations between numeric columns
- Suggests chart types (histogram, scatter, bar)
- Answers general data questions via LLM

**Example prompt:** *Paste a CSV block and ask "Analyse this data"*

### 💻 Code Assistant Agent
- Extracts code blocks from messages
- Performs AST-based static analysis (detects bare excepts, mutable defaults, etc.)
- Executes code safely in a sandboxed subprocess
- Provides LLM-powered code review
- Answers general programming questions

**Example prompt:** *"Debug this function: ```python def factorial(n): return n * factorial(n)```"*

### 📅 Scheduler Agent
- Natural language time parsing ("tomorrow", "at 3pm", "next week")
- Creates reminders in SQLite database
- Lists active reminders
- Marks reminders as complete

**Example prompt:** *"Remind me to submit the report tomorrow at 5pm"*

### 🎓 Learning Mode Agent
- Detects knowledge level from language cues (beginner/intermediate/advanced)
- Offline knowledge base for recursion, APIs, and more
- LLM-powered adaptive explanations
- Code examples scaled to skill level

**Example prompt:** *"Explain recursion to a beginner"* or *"Give me an advanced explanation of async I/O"*

### 🔧 Troubleshooter Agent
- Pattern-matches 8 common Python exceptions (KeyError, ModuleNotFoundError, etc.)
- Provides root cause + numbered fix steps
- General technical problem-solving via LLM
- 5-step debugging checklist

**Example prompt:** *"I'm getting AttributeError: 'NoneType' object has no attribute 'text'"*

---

## 🔌 MCP Server

The MCP server runs on **port 8001** as a JSON-RPC 2.0 endpoint alongside the main API.

### Available Tools

| Tool | Description |
|---|---|
| `run_code` | Execute Python in sandboxed subprocess |
| `format_code` | Lint and style-check Python code |
| `explain_error` | Get root cause + fix for Python exceptions |
| `analyze_csv` | Full statistical analysis of CSV data |
| `generate_chart_spec` | Create Chart.js config from data |
| `create_reminder` | Add reminder to SQLite DB |
| `list_reminders` | Get all active reminders |
| `explain_concept` | Concept explanation from knowledge base |
| `lookup_error` | Structured exception fix lookup |
| `system_status` | Health snapshot of Lumina system |

### Example MCP Calls

```bash
# List all tools
curl -X POST http://localhost:8001/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"list_tools","params":{},"id":1}'

# Run Python code safely
curl -X POST http://localhost:8001/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"run_code","params":{"code":"import math\nprint(math.pi)"},"id":2}'

# Get system status
curl -X POST http://localhost:8001/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"system_status","params":{},"id":3}'
```

### Adding a New Tool

```python
# In any file under backend/mcp/tools/
from backend.mcp.tool_registry import registry

@registry.register(
    name="my_tool",
    description="What this tool does",
    parameters={
        "type": "object",
        "properties": {
            "input": {"type": "string", "description": "Tool input"}
        },
        "required": ["input"]
    }
)
async def my_tool(input: str) -> dict:
    return {"result": input.upper()}
```

Then import the module in `mcp_server.py` — done!

---

## 🔐 Security

### Input Validation
All requests go through Pydantic v2 models that:
- Strip HTML tags and null bytes
- Enforce field length limits
- Validate session ID format
- Validate skill enum values

### Code Sandbox (Two-Stage)
**Stage 1 — Static AST Analysis:**
- Blocks forbidden imports: `os`, `subprocess`, `socket`, `shutil`, `ctypes`, etc.
- Blocks dangerous calls: `exec`, `eval`, `__import__`, `open`
- Blocks dangerous dunder access: `__globals__`, `__builtins__`, etc.

**Stage 2 — Subprocess Isolation:**
- Executes in a clean subprocess with blocked module registry
- Hard timeout (default: 10s)
- Output truncated to 3,000 chars
- Clean environment (`PYTHONPATH=""`)

### Authentication (JWT)
```bash
# Get a token
curl -X POST http://localhost:8000/api/token \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "demo"}'

# Use the token
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "hello"}'
```

**Demo credentials:**

| Username | Password | Role |
|---|---|---|
| `lumina` | `lumina123` | admin |
| `demo` | `demo` | user |
| `guest` | `guest` | guest |

> Auth is optional — the API works in guest mode without a token.

### Rate Limiting
Sliding-window rate limiter: **60 requests per minute per IP**.
Response headers include `X-RateLimit-Remaining` and `Retry-After`.

---

## 🛠️ CLI Tools

```bash
# Install as CLI (optional)
pip install -e .

# Or run directly
python -m backend.cli.lumina_cli [COMMAND]
```

### Commands

```bash
# System status
python -m backend.cli.lumina_cli status

# Interactive chat
python -m backend.cli.lumina_cli chat
python -m backend.cli.lumina_cli chat --skill code

# Analyse a CSV file
python -m backend.cli.lumina_cli analyze data.csv

# Debug code or error
python -m backend.cli.lumina_cli debug "ModuleNotFoundError: No module named 'pandas'"
python -m backend.cli.lumina_cli debug my_script.py

# Learn a concept
python -m backend.cli.lumina_cli learn "recursion" --level beginner
python -m backend.cli.lumina_cli learn "async/await" --level advanced

# Schedule reminders
python -m backend.cli.lumina_cli schedule --add "Review PR before EOD"
python -m backend.cli.lumina_cli schedule --list
python -m backend.cli.lumina_cli schedule --complete 2
```

---

## 📖 API Reference

### Core Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | System health + agent list |
| `GET` | `/` | Frontend UI |
| `POST` | `/api/token` | Get JWT token |
| `POST` | `/api/chat` | Chat with orchestrator |
| `POST` | `/api/execute` | Execute Python code |
| `GET` | `/api/agents` | List all agents |
| `GET` | `/api/reminders` | List active reminders |
| `POST` | `/api/mcp` | Proxy to MCP server |
| `WS` | `/ws/{session_id}` | Real-time chat WebSocket |

### Chat Request

```json
POST /api/chat
{
  "message": "Explain recursion",
  "skill": "learn",
  "context": {}
}
```

### Chat Response

```json
{
  "content": "**Recursion** means...",
  "agent_name": "LearningAdvisor",
  "skill": "learn",
  "tools_used": ["knowledge_base"],
  "metadata": {"level": "intermediate", "topic": "recursion"},
  "confidence": 1.0
}
```

### WebSocket Protocol

```javascript
// Client → Server
{"message": "Hello Lumina", "skill": "auto"}

// Server → Client (typing)
{"type": "typing", "agent": "learn"}

// Server → Client (response)
{"type": "response", "data": {AgentResponse}, "session_id": "abc123"}
```

---

## ⚙️ Configuration

All settings are in `.env` (copy from `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `API_PORT` | `8000` | FastAPI port |
| `MCP_PORT` | `8001` | MCP server port |
| `SECRET_KEY` | *(see .env.example)* | JWT signing key |
| `MAX_REQUESTS_PER_MINUTE` | `60` | Rate limit |
| `MAX_CODE_EXECUTION_TIMEOUT` | `10` | Sandbox timeout (seconds) |
| `DB_PATH` | `data/lumina.db` | SQLite database path |

---

## 🐳 Docker Deployment

```bash
# Build and start
docker compose up --build

# Background
docker compose up -d --build

# Logs
docker compose logs -f lumina

# Stop
docker compose down
```

---

## 🧪 Running Tests

```bash
# Install test dependencies (included in requirements.txt)
pip install pytest pytest-asyncio

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_security.py -v
pytest tests/test_agents.py -v
pytest tests/test_mcp.py -v

# With coverage
pip install pytest-cov
pytest tests/ --cov=backend --cov-report=html
```

---

## 📁 Project Structure

```
Lumina/
├── backend/
│   ├── main.py                    # FastAPI app + lifespan
│   ├── agents/
│   │   ├── base_agent.py          # Abstract base, no external LLM calls
│   │   ├── orchestrator.py        # ADK-style router (keyword scoring)
│   │   ├── data_agent.py          # 📊 CSV analysis + statistics
│   │   ├── code_agent.py          # 💻 Code review + sandbox execution
│   │   ├── schedule_agent.py      # 📅 SQLite reminders + NL time parsing
│   │   ├── learning_agent.py      # 🎓 Adaptive explanations
│   │   └── troubleshoot_agent.py  # 🔧 Error pattern matching
│   ├── mcp/
│   │   ├── mcp_server.py          # aiohttp JSON-RPC 2.0 server
│   │   ├── tool_registry.py       # Decorator-based tool registration
│   │   └── tools/
│   │       ├── code_tools.py      # run_code, format_code, explain_error
│   │       ├── data_tools.py      # analyze_csv, generate_chart_spec
│   │       ├── schedule_tools.py  # create/list/complete reminders
│   │       └── search_tools.py    # explain_concept, lookup_error, system_status
│   ├── security/
│   │   ├── validator.py           # Pydantic v2 request models
│   │   ├── sandbox.py             # AST validation + subprocess isolation
│   │   ├── auth.py                # JWT create/verify + FastAPI deps
│   │   └── rate_limiter.py        # Sliding-window per-IP rate limiting
│   └── cli/
│       └── lumina_cli.py          # Click CLI with Rich output
├── config/
│   └── settings.py                # pydantic-settings env-file config
├── frontend/
│   ├── index.html                 # Semantic HTML shell
│   ├── styles.css                 # Glassmorphic design system
│   └── app.js                     # WebSocket chat + markdown rendering
├── tests/
│   ├── test_security.py           # 15 security tests
│   ├── test_agents.py             # 14 agent tests
│   └── test_mcp.py                # 12 MCP tool tests
├── docs/
│   └── antigravity_demo.md        # End-to-end workflow walkthrough
├── data/                          # SQLite DB (created at runtime)
├── .env.example                   # Environment template
├── .gitignore
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-agent`
3. Add your agent in `backend/agents/`
4. Register MCP tools in `backend/mcp/tools/`
5. Add tests in `tests/`
6. Submit a PR

---

## 📜 License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ using FastAPI · Pydantic · aiohttp · Click · SQLite**

⭐ Star this repo if you find it useful!

</div>
#   L U M I N A - 
 
 