"""
Lumina Agent — Data Analysis
Interprets, statistically summarises, and visualises data from CSV or tabular input.
"""
from __future__ import annotations

import io
import re
from typing import Any, Dict, Optional

from backend.agents.base_agent import BaseAgent, AgentResponse


class DataAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="DataAnalyst",
            skill="data",
            description="Interprets data, generates statistics, and suggests visualisations",
            emoji="📊",
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_csv(text: str) -> Optional[str]:
        """Pull the first CSV-like block from free text."""
        # Look for fenced code block
        m = re.search(r"```(?:csv)?\s*\n([\s\S]+?)```", text)
        if m:
            return m.group(1)
        # Detect raw CSV: multiple lines with commas
        lines = [l for l in text.splitlines() if "," in l]
        if len(lines) >= 2:
            return "\n".join(lines)
        return None

    @staticmethod
    def _analyse_csv(csv_text: str) -> str:
        """Parse CSV with pandas and return a markdown summary."""
        try:
            import pandas as pd
            import numpy as np

            df = pd.read_csv(io.StringIO(csv_text))
            rows, cols = df.shape
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            cat_cols = df.select_dtypes(include=["object"]).columns.tolist()

            lines = [
                f"### 📊 Dataset Overview",
                f"- **Rows:** {rows:,}  |  **Columns:** {cols}",
                f"- **Numeric columns:** {', '.join(numeric_cols) or 'none'}",
                f"- **Categorical columns:** {', '.join(cat_cols) or 'none'}",
                f"- **Missing values:** {int(df.isnull().sum().sum())}",
                "",
            ]

            if numeric_cols:
                desc = df[numeric_cols].describe().round(3)
                lines.append("### 📈 Descriptive Statistics")
                lines.append(desc.to_markdown())
                lines.append("")

            if cat_cols:
                lines.append("### 🏷️ Categorical Columns — Top Values")
                for col in cat_cols[:3]:
                    top = df[col].value_counts().head(5)
                    lines.append(f"\n**{col}:**")
                    for val, cnt in top.items():
                        lines.append(f"  - `{val}`: {cnt}")
                lines.append("")

            if numeric_cols:
                corr = df[numeric_cols].corr().round(2)
                if corr.shape[0] > 1:
                    # find strongest pair
                    pairs = []
                    for i, c1 in enumerate(numeric_cols):
                        for c2 in numeric_cols[i + 1:]:
                            pairs.append((abs(corr.loc[c1, c2]), c1, c2, corr.loc[c1, c2]))
                    pairs.sort(reverse=True)
                    if pairs:
                        _, c1, c2, r = pairs[0]
                        lines.append(f"### 🔗 Strongest Correlation")
                        lines.append(f"  **{c1}** ↔ **{c2}** — r = {r:.2f}")
                        lines.append("")

            lines.append("### 💡 Suggested Visualisations")
            if numeric_cols:
                lines.append(f"  - Histogram of **{numeric_cols[0]}**")
            if len(numeric_cols) >= 2:
                lines.append(f"  - Scatter plot: **{numeric_cols[0]}** vs **{numeric_cols[1]}**")
            if cat_cols:
                lines.append(f"  - Bar chart of **{cat_cols[0]}** value counts")

            return "\n".join(lines)

        except ImportError:
            return (
                "⚠️ pandas/numpy not installed. "
                "Run `pip install pandas numpy` to enable full data analysis."
            )
        except Exception as exc:
            return f"⚠️ Could not parse data: {exc}"

    # ── Fallback (no LLM) ─────────────────────────────────────────────────────

    @staticmethod
    def _fallback(message: str) -> str:
        kw = message.lower()
        if "mean" in kw or "average" in kw:
            return (
                "**Mean / Average**\n\n"
                "Mean = Σ(values) / n\n\n"
                "In Python:\n```python\nimport statistics\ndata = [10, 20, 30]\nprint(statistics.mean(data))  # 20\n```"
            )
        if "outlier" in kw:
            return (
                "**Outlier Detection**\n\n"
                "Common methods:\n"
                "- **IQR method**: flag values outside [Q1 - 1.5×IQR, Q3 + 1.5×IQR]\n"
                "- **Z-score method**: flag values where |z| > 3\n\n"
                "```python\nimport pandas as pd\nQ1, Q3 = df['col'].quantile([0.25, 0.75])\nIQR = Q3 - Q1\noutliers = df[(df['col'] < Q1-1.5*IQR) | (df['col'] > Q3+1.5*IQR)]\n```"
            )
        return (
            "**📊 Lumina Data Analysis Capabilities**\n\n"
            "Paste CSV data directly in your message and I'll:\n"
            "- Compute descriptive statistics (mean, std, min, max, quartiles)\n"
            "- Identify missing values and data types\n"
            "- Detect correlations between numeric columns\n"
            "- Suggest appropriate chart types\n"
            "- Highlight categorical distributions\n\n"
            "**Example prompt:** Paste a CSV block like:\n"
            "```csv\nname,age,salary\nAlice,30,70000\nBob,25,55000\nCarol,35,90000\n```"
        )

    # ── Main entry point ──────────────────────────────────────────────────────

    async def process(self, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        tools_used: list[str] = []
        csv_block = self._extract_csv(message)

        if csv_block:
            analysis = self._analyse_csv(csv_block)
            tools_used.append("analyze_csv")
            content = analysis
        else:
            # Answer general data questions with the built-in engine
            content = self._fallback(message)
            tools_used.append("fallback_engine")

        return AgentResponse(
            content=content,
            agent_name=self.name,
            skill=self.skill,
            tools_used=tools_used,
            metadata={"has_csv": csv_block is not None},
        )
