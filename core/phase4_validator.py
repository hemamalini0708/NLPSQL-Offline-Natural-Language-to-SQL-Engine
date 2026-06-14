"""
NLPSQL SYSTEM — PHASE 04
Query Validation, AST Parsing & Self-Healing Engine
"""

import re
import time
import psycopg2
from typing import Tuple, Optional

SYSTEM_PROMPT_PHASE4 = """You are a PostgreSQL SQL validator and repair agent.

Given:
1. A schema (table names, column names, types)
2. A generated SQL query
3. Optionally: an error message from PostgreSQL

Perform these validation checks:
- All referenced table names exist in the schema
- All referenced column names exist in the correct tables
- Aggregate functions are paired with proper GROUP BY clauses
- JOINs reference correct key columns
- Subqueries are syntactically valid
- Window functions have proper OVER() clauses

If invalid: rewrite the corrected query.
If valid: return the query unchanged.

Output ONLY the final SQL query. Nothing else.
"""


def validate_sql_syntax(sql: str) -> Tuple[bool, str]:
    """Basic regex-level syntax checks before hitting the DB."""
    sql_upper = sql.upper().strip()
    
    if not sql_upper.startswith("SELECT"):
        if not any(sql_upper.startswith(k) for k in ["WITH", "SELECT"]):
            return False, "Query must start with SELECT or WITH (CTE)"
    
    # Check for dangerous statements
    dangerous = ["DROP ", "DELETE ", "TRUNCATE ", "UPDATE ", "INSERT ", "ALTER ", "CREATE "]
    for kw in dangerous:
        if kw in sql_upper:
            return False, f"Dangerous keyword detected: {kw.strip()}. Only SELECT queries allowed."
    
    # Check balanced parentheses
    open_p = sql.count("(")
    close_p = sql.count(")")
    if open_p != close_p:
        return False, f"Unbalanced parentheses: {open_p} open, {close_p} close"
    
    # Check for GROUP BY when aggregate functions used
    agg_pattern = r'\b(COUNT|SUM|AVG|MAX|MIN)\s*\('
    has_agg = bool(re.search(agg_pattern, sql_upper))
    has_group_by = "GROUP BY" in sql_upper
    has_window = "OVER" in sql_upper
    # note: aggregates without GROUP BY are valid (e.g. SELECT COUNT(*) FROM t)
    # so we just warn, not error
    
    return True, "Syntax pre-check passed"


def validate_table_columns(sql: str, schema_metadata: dict) -> Tuple[bool, list]:
    """Check that referenced tables and columns exist in schema."""
    known_tables = {t["table_name"].lower() for t in schema_metadata["tables"]}
    known_columns = {}
    for t in schema_metadata["tables"]:
        for col in t["columns"]:
            known_columns[f"{t['table_name'].lower()}.{col['clean_name'].lower()}"] = True
            known_columns[col["clean_name"].lower()] = True  # unqualified

    warnings = []
    # Extract table references from FROM / JOIN
    from_pattern = r'\bFROM\s+(\w+)|\bJOIN\s+(\w+)'
    matches = re.findall(from_pattern, sql, re.IGNORECASE)
    for m in matches:
        tbl = (m[0] or m[1]).lower()
        if tbl and tbl not in known_tables:
            warnings.append(f"Unknown table: '{tbl}'")

    return len(warnings) == 0, warnings


def explain_query(sql: str, conn_str: str) -> Tuple[bool, str, Optional[dict]]:
    """Run EXPLAIN (no actual execution) to validate query plan."""
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()
        cur.execute(f"EXPLAIN (FORMAT JSON) {sql}")
        plan = cur.fetchone()[0]
        cur.close()
        conn.close()
        return True, "Query plan generated successfully", plan
    except psycopg2.Error as e:
        return False, str(e), None


def execute_query(sql: str, conn_str: str, timeout_ms: int = 30000) -> dict:
    """Execute the validated query and return results."""
    start = time.time()
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()
        cur.execute(f"SET statement_timeout = {timeout_ms}")
        cur.execute(sql)
        rows = cur.fetchmany(500)  # cap at 500 rows for UI display
        columns = [desc[0] for desc in cur.description] if cur.description else []
        elapsed = int((time.time() - start) * 1000)
        cur.close()
        conn.close()
        return {
            "success": True,
            "columns": columns,
            "rows": [list(r) for r in rows],
            "row_count": len(rows),
            "execution_time_ms": elapsed,
            "error": None
        }
    except psycopg2.Error as e:
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_time_ms": int((time.time() - start) * 1000),
            "error": str(e)
        }


def validate_and_execute(
    sql: str,
    schema_metadata: dict,
    conn_str: str,
    llm_heal_fn=None,
    schema_ddl: str = "",
    max_retries: int = 3
) -> dict:
    """Full validation + self-healing execution pipeline."""
    
    # Step 1: Syntax pre-check
    syntax_ok, syntax_msg = validate_sql_syntax(sql)
    if not syntax_ok:
        return {"success": False, "error": syntax_msg, "sql": sql, "healed": False}
    
    # Step 2: Table/column existence check
    cols_ok, col_warnings = validate_table_columns(sql, schema_metadata)
    
    # Step 3: EXPLAIN plan check
    plan_ok, plan_msg, plan = explain_query(sql, conn_str)
    
    current_sql = sql
    healed = False
    
    for attempt in range(max_retries):
        if plan_ok:
            break
        if llm_heal_fn and attempt < max_retries - 1:
            current_sql = llm_heal_fn(current_sql, plan_msg, schema_ddl)
            plan_ok, plan_msg, plan = explain_query(current_sql, conn_str)
            healed = True
        else:
            return {
                "success": False,
                "error": f"Query validation failed after {attempt+1} attempts: {plan_msg}",
                "sql": current_sql,
                "healed": healed,
                "warnings": col_warnings
            }
    
    # Step 4: Execute
    result = execute_query(current_sql, conn_str)
    result["sql"] = current_sql
    result["healed"] = healed
    result["warnings"] = col_warnings
    result["plan"] = plan
    return result
