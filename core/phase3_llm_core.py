"""
NLPSQL SYSTEM — PHASE 03
Offline LLM Core — SQL Generator with RAG & Few-Shot
Uses Ollama for 100% offline LLM inference.
"""

import json
import requests
from typing import List, Optional
from config import LLM_MODEL

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = LLM_MODEL

# ─────────────────────────────────────────────
# MASTER SYSTEM PROMPT — The core SQL generator
# ─────────────────────────────────────────────
SYSTEM_PROMPT_PHASE3 = """You are an expert PostgreSQL query generator for an MNC-grade internal analytics system called NLPSQL.

You will receive:
1. SCHEMA CONTEXT — table names, column names, types, and semantic descriptions
2. FEW-SHOT EXAMPLES — similar NL→SQL pairs retrieved from a vector database
3. USER QUESTION — a natural language question from a business user

Your task is to generate a syntactically correct and optimized PostgreSQL query.

=== THINKING PROCESS (Mandatory) ===
1. LIST TABLES: Which tables are needed based on the user's intent?
2. VERIFY COLUMNS: For each table, which columns will you use? (Check the SCHEMA CONTEXT carefully to ensure the column exists in that specific table).
3. RATIONALE: Explain your join logic and choice of columns.
4. SQL: Write the final PostgreSQL query inside a ```sql code block.

=== STRICT RULES (NEVER VIOLATE) ===

1. USE ONLY PostgreSQL syntax.
2. ONLY use table/column names from the SCHEMA CONTEXT. Never hallucinate.
3. Always qualify column names with their table name (e.g., orders.order_id).
4. For trends/rankings, use window functions (RANK, SUM OVER, etc.).
5. If columns needed are in different tables, you MUST perform a JOIN.
6. CRITICAL: NEVER use window functions inside a GROUP BY clause.
7. IMPORTANT: PostgreSQL DATE columns do NOT support YEAR() or LIKE. Use EXTRACT(YEAR FROM column) = 2023 instead.
8. Use proper JOINs (INNER/LEFT). No implicit comma joins.
9. Always use GROUP BY when using aggregate functions.
10. Add LIMIT 1000 by default.
11. Output the SQL inside a ```sql code block. Any explanations must come BEFORE the block.
"""


def build_rag_prompt(
    question: str,
    schema_context: List[dict],
    few_shot_examples: List[dict],
    full_schema_ddl: str
) -> str:
    schema_block = "=== SCHEMA CONTEXT ===\n"
    schema_block += full_schema_ddl + "\n\n"
    schema_block += "=== RELEVANT SCHEMA FRAGMENTS (by semantic similarity) ===\n"
    for item in schema_context:
        schema_block += f"- {item['description']}\n"

    examples_block = "\n=== FEW-SHOT EXAMPLES (similar past queries) ===\n"
    for i, ex in enumerate(few_shot_examples, 1):
        examples_block += f"\nExample {i} [{ex['complexity']}]:\n"
        examples_block += f"Q: {ex['question']}\n"
        examples_block += f"SQL:\n{ex['sql']}\n"

    return (
        schema_block
        + examples_block
        + f"\n=== USER QUESTION ===\n{question}\n\n"
        + "Generate the PostgreSQL query:"
    )


def call_ollama(prompt: str, model: str = DEFAULT_MODEL, temperature: float = 0.1) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "system": SYSTEM_PROMPT_PHASE3,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 1024,
            "top_p": 0.9,
            "repeat_penalty": 1.1
        }
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=600)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            "Ollama is not running. Start it with: ollama serve\n"
            "Then pull a model: ollama pull sqlcoder"
        )
    except Exception as e:
        raise RuntimeError(f"Ollama call failed: {e}")


def clean_sql_output(raw: str) -> str:
    """Extract SQL from code blocks or find the first SELECT/WITH."""
    import re
    # Try to find content in ```sql ... ``` or ``` ... ```
    match = re.search(r"```(?:sql)?(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Fallback: Find the first SELECT, WITH, or comment block
    match = re.search(r"(SELECT|WITH|--).*$", raw, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(0).strip()
    
    return raw.strip()


def generate_sql(
    question: str,
    schema_context: List[dict],
    few_shot_examples: List[dict],
    full_schema_ddl: str,
    model: str = DEFAULT_MODEL
) -> dict:
    prompt = build_rag_prompt(question, schema_context, few_shot_examples, full_schema_ddl)
    raw_output = call_ollama(prompt, model=model)
    sql = clean_sql_output(raw_output)
    return {
        "question": question,
        "sql": sql,
        "prompt_used": prompt,
        "model": model
    }


# ─────────────────────────────────────────────
# SELF-HEALING RETRY PROMPT
# ─────────────────────────────────────────────
SELF_HEAL_SYSTEM_PROMPT = """You are a PostgreSQL query repair expert.

You will receive:
1. A schema definition
2. A broken SQL query
3. The error message from PostgreSQL

Your task: Fix the SQL query so it runs correctly.

Rules:
- Only use table/column names from the schema
- Output ONLY the corrected SQL, no explanation
- Preserve the original intent of the query
"""

def self_heal_sql(broken_sql: str, error_msg: str, schema_ddl: str, model: str = DEFAULT_MODEL) -> str:
    heal_prompt = (
        f"=== SCHEMA ===\n{schema_ddl}\n\n"
        f"=== BROKEN SQL ===\n{broken_sql}\n\n"
        f"=== ERROR ===\n{error_msg}\n\n"
        "Fix the SQL and return ONLY the corrected query:"
    )
    payload = {
        "model": model,
        "prompt": heal_prompt,
        "system": SELF_HEAL_SYSTEM_PROMPT,
        "stream": False,
        "options": {"temperature": 0.05, "num_predict": 1024}
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=300)
    resp.raise_for_status()
    raw = resp.json().get("response", "").strip()
    return clean_sql_output(raw)
