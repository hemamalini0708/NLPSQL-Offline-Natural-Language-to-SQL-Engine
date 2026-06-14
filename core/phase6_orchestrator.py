"""
NLPSQL SYSTEM — PHASE 06
Production Orchestrator — ties all phases together
"""

import json
import time
import psycopg2
from typing import Optional
from core.phase1_ingestion import analyze_csv, save_schema_metadata, generate_basic_ddl
from core.phase2_embeddings import (
    retrieve_similar_schema, retrieve_similar_examples,
    setup_pgvector, embed_and_store_schema, embed_and_store_examples, get_local_embedder
)
from core.phase3_llm_core import generate_sql, self_heal_sql, DEFAULT_MODEL
from core.phase4_validator import validate_and_execute
from core.phase5_router import classify_complexity, get_complexity_system_prompt


SYSTEM_PROMPT_PHASE6 = """You are the NLPSQL production orchestrator.

Your responsibilities:
1. Accept natural language questions from business users
2. Route the question through: classify → retrieve context → generate SQL → validate → execute
3. If execution fails, trigger self-healing (up to 3 retries)
4. Log every query with: question, generated SQL, complexity, execution time, row count, success/fail
5. Return structured results including: SQL, result rows, execution metadata, confidence score

Never expose internal system errors directly to users — return friendly error messages instead.
Always log failures for the fine-tuning pipeline.
"""

SCHEMA_PATH = "data/schema_metadata.json"


def load_schema() -> Optional[dict]:
    try:
        with open(SCHEMA_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def get_full_ddl(schema_metadata: dict) -> str:
    contexts = []
    for t in schema_metadata.get("tables", []):
        # Use the detailed LLM context if available, fallback to basic DDL
        if "llm_context" in t:
            contexts.append(t["llm_context"])
        elif "basic_ddl" in t:
            contexts.append(t["basic_ddl"])
    return "\n\n".join(contexts)


def log_query(
    conn_str: str,
    question: str,
    sql: str,
    complexity: str,
    execution_time_ms: int,
    row_count: int,
    was_valid: bool,
    error_message: Optional[str] = None
):
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO nlpsql_query_history 
               (question, generated_sql, complexity, execution_time_ms, row_count, was_valid, error_message)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (question, sql, complexity, execution_time_ms, row_count, was_valid, error_message)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass  # Never let logging crash the main pipeline


def save_feedback(conn_str: str, query_id: int, feedback: int):
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()
        cur.execute(
            "UPDATE nlpsql_query_history SET feedback = %s WHERE id = %s",
            (feedback, query_id)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass


def get_query_history(conn_str: str, limit: int = 50) -> list:
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()
        cur.execute(
            """SELECT id, question, generated_sql, complexity, execution_time_ms,
                      row_count, was_valid, error_message, feedback, created_at
               FROM nlpsql_query_history
               ORDER BY created_at DESC
               LIMIT %s""",
            (limit,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{
            "id": r[0], "question": r[1], "sql": r[2], "complexity": r[3],
            "execution_time_ms": r[4], "row_count": r[5], "was_valid": r[6],
            "error": r[7], "feedback": r[8], "created_at": str(r[9])
        } for r in rows]
    except Exception:
        return []


from config import DB_URL, LLM_MODEL, USE_LLM_ROUTER, MAX_HEAL_RETRIES

def run_pipeline(
    question: str,
    conn_str: str,
    model: str = LLM_MODEL,
    embedder=None
) -> dict:
    """Main pipeline: question → SQL → results."""
    start_total = time.time()

    schema_metadata = load_schema()
    if not schema_metadata:
        return {"success": False, "error": "Schema not loaded. Please run data ingestion first.", "sql": ""}

    # Phase 5: Classify complexity
    if USE_LLM_ROUTER:
        print(f"[SYSTEM] Loading model for classification: {model}...")
    complexity = classify_complexity(question, model=model, use_llm=USE_LLM_ROUTER)
    print(f"[SYSTEM] Complexity classified as: {complexity}")

    # Phase 2: Retrieve context
    print("[SYSTEM] Generating query embeddings...")
    if embedder is None:
        embedder = get_local_embedder()

    print("[SYSTEM] Retrieving relevant schema context and examples...")
    schema_context = retrieve_similar_schema(question, conn_str, embedder, top_k=8)
    few_shot_examples = retrieve_similar_examples(question, conn_str, embedder, top_k=5)
    full_ddl = get_full_ddl(schema_metadata)
    print(f"[SYSTEM] Context built: {len(schema_context)} schema fragments, {len(few_shot_examples)} examples.")

    # Phase 3: Generate SQL
    print("[SYSTEM] Writing SQL query via LLM...")
    gen_result = generate_sql(
        question=question,
        schema_context=schema_context,
        few_shot_examples=few_shot_examples,
        full_schema_ddl=full_ddl,
        model=model
    )
    sql = gen_result["sql"]

    # Phase 4: Validate + self-heal + execute
    print("[SYSTEM] Validating and executing SQL...")
    def heal_fn(broken_sql, error_msg, schema_ddl):
        print(f"[SYSTEM] Self-healing triggered due to error: {error_msg}")
        return self_heal_sql(broken_sql, error_msg, schema_ddl, model=model)

    exec_result = validate_and_execute(
        sql=sql,
        schema_metadata=schema_metadata,
        conn_str=conn_str,
        llm_heal_fn=heal_fn,
        schema_ddl=full_ddl,
        max_retries=MAX_HEAL_RETRIES
    )
    if exec_result.get("success"):
        print(f"[SYSTEM] Execution successful. Rows returned: {exec_result.get('row_count')}")
    else:
        print(f"[SYSTEM] Execution failed: {exec_result.get('error')}")

    total_ms = int((time.time() - start_total) * 1000)

    # Phase 6: Log
    log_query(
        conn_str=conn_str,
        question=question,
        sql=exec_result.get("sql", sql),
        complexity=complexity,
        execution_time_ms=total_ms,
        row_count=exec_result.get("row_count", 0),
        was_valid=exec_result.get("success", False),
        error_message=exec_result.get("error")
    )

    return {
        "success": exec_result.get("success", False),
        "question": question,
        "sql": exec_result.get("sql", sql),
        "complexity": complexity,
        "columns": exec_result.get("columns", []),
        "rows": exec_result.get("rows", []),
        "row_count": exec_result.get("row_count", 0),
        "execution_time_ms": total_ms,
        "healed": exec_result.get("healed", False),
        "warnings": exec_result.get("warnings", []),
        "error": exec_result.get("error"),
        "schema_context_used": len(schema_context),
        "examples_used": len(few_shot_examples)
    }
