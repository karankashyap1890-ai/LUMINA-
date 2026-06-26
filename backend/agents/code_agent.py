"""
Lumina Agent — Code Assistant
Reviews code, explains errors, and safely executes Python snippets.
"""
from __future__ import annotations

import ast
import re
from typing import Any, Dict, List, Optional

from backend.agents.base_agent import BaseAgent, AgentResponse
from backend.security.sandbox import execute_code_safely


class CodeAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="CodeAssistant",
            skill="code",
            description="Reviews code, debugs errors, and executes Python safely",
            emoji="💻",
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_code_block(text: str) -> Optional[str]:
        """Extract first fenced code block from message."""
        m = re.search(r"```(?:python|py)?\s*\n([\s\S]+?)```", text)
        if m:
            return m.group(1).strip()
        # Heuristic: multi-line text starting with 'def', 'class', 'import'
        lines = text.splitlines()
        code_lines = [l for l in lines if l.strip().startswith(
            ("def ", "class ", "import ", "from ", "for ", "if ", "while ", "#", "    ", "\t")
        )]
        if len(code_lines) >= 2:
            return "\n".join(code_lines)
        return None

    @staticmethod
    def _ast_review(code: str) -> List[str]:
        """Static analysis hints from the AST."""
        hints: List[str] = []
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return [f"🔴 **Syntax error** at line {exc.lineno}: `{exc.msg}`"]

        for node in ast.walk(tree):
            # Bare except
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                hints.append("⚠️ Bare `except:` catches *all* exceptions — prefer `except Exception as e:`")
            # Comparison with None using ==
            if isinstance(node, ast.Compare):
                for op in node.ops:
                    if isinstance(op, (ast.Eq, ast.NotEq)):
                        for comp in node.comparators:
                            if isinstance(comp, ast.Constant) and comp.value is None:
                                hints.append("⚠️ Use `is None` / `is not None` instead of `== None`")
            # Mutable default argument
            if isinstance(node, ast.FunctionDef):
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        hints.append(
                            f"⚠️ Mutable default argument in `{node.name}()` — "
                            "use `None` as default and assign inside the function"
                        )
            # print without f-string (style)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "print":
                    if node.args and isinstance(node.args[0], ast.BinOp):
                        hints.append("💡 Consider f-strings instead of string concatenation in print()")

        if not hints:
            hints.append("✅ No obvious code quality issues detected")
        return hints

    @staticmethod
    def _fallback(message: str) -> str:
        kw = message.lower()
        if "recursion" in kw:
            return (
                "**Recursion Error Fix**\n\n"
                "Python's default recursion limit is **1000**. Solutions:\n"
                "```python\nimport sys\nsys.setrecursionlimit(5000)  # increase limit\n```\n"
                "Or refactor to an **iterative** approach using a stack:\n"
                "```python\ndef factorial_iter(n):\n    result = 1\n    while n > 1:\n        result *= n; n -= 1\n    return result\n```"
            )
        if "async" in kw or "await" in kw:
            return (
                "**Python Async / Await Tips**\n\n"
                "- Use `async def` for coroutines\n"
                "- `await` pauses the coroutine until the awaitable resolves\n"
                "- Run with `asyncio.run(main())`\n\n"
                "```python\nimport asyncio\n\nasync def fetch(url):\n    await asyncio.sleep(1)  # simulate I/O\n    return f'data from {url}'\n\nasync def main():\n    result = await fetch('https://example.com')\n    print(result)\n\nasyncio.run(main())\n```"
            )
        return (
            "**💻 Lumina Code Assistant**\n\n"
            "I can help you with:\n"
            "- **Code review** — paste your code and I'll analyse it\n"
            "- **Debugging** — share the error traceback\n"
            "- **Execution** — I'll run your Python snippet safely\n"
            "- **Explanations** — ask how any concept works\n\n"
            "**Try:** Paste a code block using triple backticks:\n"
            "````\n```python\ndef hello(name):\n    return f'Hello, {name}!'\nprint(hello('Lumina'))\n```\n````"
        )

    # ── Main entry point ──────────────────────────────────────────────────────

    async def process(self, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        tools_used: List[str] = []
        parts: List[str] = []

        code_block = self._extract_code_block(message)

        if code_block:
            # ── Static review
            hints = self._ast_review(code_block)
            tools_used.append("ast_reviewer")
            parts.append("### 🔍 Static Analysis\n" + "\n".join(f"- {h}" for h in hints))

            # ── Safe execution
            run_kw = any(w in message.lower() for w in ["run", "execute", "output", "result", "what does"])
            if run_kw or "```" in message:
                exec_result = await execute_code_safely(code_block)
                tools_used.append("sandbox_executor")
                if exec_result["security_blocked"]:
                    parts.append(f"\n### 🔒 Security\n{exec_result['error']}")
                elif exec_result["success"]:
                    output = exec_result["output"] or "*(no output)*"
                    parts.append(
                        f"\n### ✅ Execution Output ({exec_result['execution_time']}s)\n```\n{output}\n```"
                    )
                else:
                    parts.append(
                        f"\n### ❌ Execution Error\n```\n{exec_result['error']}\n```"
                    )

            # No LLM supplement needed — static analysis is the complete review
            content = "\n".join(parts)

        else:
            # Answer general coding questions with the built-in engine
            content = self._fallback(message)
            tools_used.append("fallback_engine")

        return AgentResponse(
            content=content,
            agent_name=self.name,
            skill=self.skill,
            tools_used=tools_used,
            metadata={"has_code": code_block is not None},
        )
