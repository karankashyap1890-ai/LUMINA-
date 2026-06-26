"""
Lumina MCP Tools — Data Tools
CSV analysis and chart spec generation exposed over MCP.
"""
from __future__ import annotations

import io
from typing import Any, Dict, List

from backend.mcp.tool_registry import registry


@registry.register(
    name="analyze_csv",
    description="Parse CSV text and return descriptive statistics, column info, and visualisation suggestions.",
    parameters={
        "type": "object",
        "properties": {
            "csv_text": {"type": "string", "description": "Raw CSV content as a string"},
            "max_rows": {"type": "integer", "description": "Maximum rows to analyse (default 1000)"},
        },
        "required": ["csv_text"],
    },
)
async def analyze_csv(csv_text: str, max_rows: int = 1000) -> Dict[str, Any]:
    """Full statistical analysis of a CSV string."""
    try:
        import pandas as pd
        import numpy as np

        df = pd.read_csv(io.StringIO(csv_text), nrows=max_rows)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = df.select_dtypes(include=["object"]).columns.tolist()

        stats = {}
        if numeric_cols:
            desc = df[numeric_cols].describe()
            stats = desc.to_dict()

        missing = df.isnull().sum().to_dict()

        # Correlation matrix (top pairs)
        correlations: List[Dict] = []
        if len(numeric_cols) >= 2:
            corr = df[numeric_cols].corr()
            for i, c1 in enumerate(numeric_cols):
                for c2 in numeric_cols[i + 1:]:
                    correlations.append({
                        "col1": c1,
                        "col2": c2,
                        "r": round(float(corr.loc[c1, c2]), 3),
                    })
            correlations.sort(key=lambda x: abs(x["r"]), reverse=True)
            correlations = correlations[:5]

        chart_suggestions: List[Dict] = []
        if numeric_cols:
            chart_suggestions.append({"type": "histogram", "column": numeric_cols[0]})
        if len(numeric_cols) >= 2:
            chart_suggestions.append({"type": "scatter", "x": numeric_cols[0], "y": numeric_cols[1]})
        if cat_cols:
            chart_suggestions.append({"type": "bar", "column": cat_cols[0]})

        return {
            "success": True,
            "shape": {"rows": int(df.shape[0]), "cols": int(df.shape[1])},
            "columns": list(df.columns),
            "numeric_columns": numeric_cols,
            "categorical_columns": cat_cols,
            "missing_values": {k: int(v) for k, v in missing.items() if v > 0},
            "statistics": {k: {sk: round(sv, 4) for sk, sv in v.items()} for k, v in stats.items()},
            "top_correlations": correlations,
            "chart_suggestions": chart_suggestions,
        }

    except ImportError:
        return {"success": False, "error": "pandas/numpy not installed"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@registry.register(
    name="generate_chart_spec",
    description="Generate a Chart.js-compatible spec from column names and chart type.",
    parameters={
        "type": "object",
        "properties": {
            "chart_type": {"type": "string", "enum": ["bar", "line", "scatter", "pie"]},
            "labels": {"type": "array", "items": {"type": "string"}},
            "values": {"type": "array", "items": {"type": "number"}},
            "title": {"type": "string"},
        },
        "required": ["chart_type", "labels", "values"],
    },
)
async def generate_chart_spec(
    chart_type: str,
    labels: List[str],
    values: List[float],
    title: str = "Chart",
) -> Dict[str, Any]:
    """Return a Chart.js config object ready for frontend rendering."""
    colors = [
        "rgba(99,102,241,0.8)", "rgba(34,211,238,0.8)", "rgba(16,185,129,0.8)",
        "rgba(245,158,11,0.8)", "rgba(239,68,68,0.8)", "rgba(236,72,153,0.8)",
    ]
    return {
        "type": chart_type,
        "data": {
            "labels": labels,
            "datasets": [{
                "label": title,
                "data": values,
                "backgroundColor": colors[: len(values)],
                "borderColor": colors[: len(values)],
                "borderWidth": 2,
            }],
        },
        "options": {
            "responsive": True,
            "plugins": {"legend": {"position": "top"}, "title": {"display": True, "text": title}},
        },
    }
