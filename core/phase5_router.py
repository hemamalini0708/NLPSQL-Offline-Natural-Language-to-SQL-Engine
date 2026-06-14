"""
NLPSQL SYSTEM — PHASE 05
Query Complexity Router & Classifier
"""

import re
import requests
from config import LLM_MODEL, USE_LLM_ROUTER

OLLAMA_URL = "http://localhost:11434/api/generate"

SYSTEM_PROMPT_PHASE5 = """You are a SQL complexity classifier for an enterprise NL-to-SQL system.

Classify the user's natural language question into exactly ONE of these complexity levels:

SIMPLE   — Single table lookup, basic WHERE/ORDER BY, no joins, no aggregation
MEDIUM   — 2-table JOIN, or basic aggregation (COUNT/SUM/AVG), or simple GROUP BY
HARD     — 3+ table JOINs, subqueries, HAVING clause, multiple aggregations
ADVANCED — Window functions (ROW_NUMBER/RANK/LAG/LEAD), CTEs, percentiles, time series
ULTRA    — Recursive CTEs, correlated subqueries, multi-step pipelines, pivot-style analysis

Output ONLY the level label, nothing else. Example: ADVANCED
"""

COMPLEXITY_PROMPT_TEMPLATES = {
    "SIMPLE": """Generate a simple PostgreSQL SELECT query.
Use a single table with basic WHERE, ORDER BY, and LIMIT clauses.
No JOINs, no subqueries, no aggregations unless explicitly needed.
Return only the SQL.""",

    "MEDIUM": """Generate a PostgreSQL query involving:
- A JOIN between 2 tables, OR
- Basic aggregation (COUNT, SUM, AVG, MAX, MIN) with GROUP BY
Keep it straightforward. Return only the SQL.""",

    "HARD": """Generate a complex PostgreSQL query involving:
- Multiple JOINs (3+ tables), AND/OR
- Subqueries in WHERE or FROM clause, AND/OR
- HAVING clause with conditions on aggregates
Use proper table aliases. Return only the SQL.""",

    "ADVANCED": """Generate an advanced PostgreSQL analytical query using:
- Window functions (ROW_NUMBER, RANK, DENSE_RANK, LAG, LEAD, SUM OVER, AVG OVER PARTITION BY)
- CTEs (WITH clauses) for multi-step logic
- Complex GROUP BY with ROLLUP or GROUPING SETS if appropriate
Return only the SQL.""",

    "ULTRA": """Generate a highly complex PostgreSQL analytical query using:
- Multiple CTEs chained together
- Correlated subqueries where needed
- Window functions combined with aggregations
- Multi-step analytical pipeline (compute intermediate results, then aggregate further)
- Use FILTER clauses on aggregates if appropriate
Break down the problem into logical CTE steps. Return only the SQL."""
}


def classify_complexity(question: str, model: str = "qwen2.5-coder:1.5b", use_llm: bool = True) -> str:
    """Use LLM or heuristic to classify question complexity."""
    if not use_llm:
        return classify_complexity_heuristic(question)
    
    try:
        payload = {
            "model": model,
            "prompt": f"Question: {question}\n\nClassify:",
            "system": SYSTEM_PROMPT_PHASE5,
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": 10}
        }
        resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
        resp.raise_for_status()
        result = resp.json().get("response", "").strip().upper()
        for level in ["ULTRA", "ADVANCED", "HARD", "MEDIUM", "SIMPLE"]:
            if level in result:
                return level
    except Exception:
        pass
    return classify_complexity_heuristic(question)


def classify_complexity_heuristic(question: str) -> str:
    """Rule-based fallback classifier (no LLM needed)."""
    q = question.lower()

    ultra_signals = [
        "recursive", "hierarchy", "tree", "path", "cumulative over time",
        "pivot", "transpose", "cohort", "retention", "multi-step", "chain"
    ]
    advanced_signals = [
        "rank", "ranking", "top n per", "running total", "moving average",
        "lag", "lead", "previous", "next", "percentile", "window",
        "year over year", "month over month", "trend"
    ]
    hard_signals = [
        "join", "across", "relate", "combine", "match", "compare",
        "having", "subquery", "nested", "multiple", "all three", "between tables"
    ]
    medium_signals = [
        "count", "sum", "average", "avg", "total", "group by", "per",
        "how many", "what is the total", "breakdown by", "grouped"
    ]

    if any(s in q for s in ultra_signals):
        return "ULTRA"
    if any(s in q for s in advanced_signals):
        return "ADVANCED"
    if any(s in q for s in hard_signals):
        return "HARD"
    if any(s in q for s in medium_signals):
        return "MEDIUM"
    return "SIMPLE"


def get_complexity_system_prompt(complexity: str) -> str:
    return COMPLEXITY_PROMPT_TEMPLATES.get(complexity, COMPLEXITY_PROMPT_TEMPLATES["MEDIUM"])


def get_complexity_color(complexity: str) -> str:
    colors = {
        "SIMPLE": "#22c55e",
        "MEDIUM": "#3b82f6",
        "HARD": "#f59e0b",
        "ADVANCED": "#f97316",
        "ULTRA": "#ef4444"
    }
    return colors.get(complexity, "#6b7280")


def get_complexity_badge(complexity: str) -> str:
    icons = {
        "SIMPLE": "🟢",
        "MEDIUM": "🔵",
        "HARD": "🟡",
        "ADVANCED": "🟠",
        "ULTRA": "🔴"
    }
    return f"{icons.get(complexity, '⚪')} {complexity}"
