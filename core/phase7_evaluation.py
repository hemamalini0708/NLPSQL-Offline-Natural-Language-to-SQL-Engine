"""
NLPSQL SYSTEM — PHASE 07
Accuracy Evaluation & Fine-Tuning Data Loop
"""

import json
import psycopg2
from typing import List, Optional

SYSTEM_PROMPT_PHASE7 = """You are an SQL evaluation and fine-tuning expert for the NLPSQL system.

Your tasks:
1. Compare a GOLD SQL query against a GENERATED SQL query for the same NL question
2. Execute both against the database and compare result sets
3. Score: 1.0 if result sets are identical, 0.5 if partially correct, 0.0 if wrong
4. For failed queries, identify the root cause:
   - Wrong table used
   - Missing JOIN
   - Wrong aggregation
   - Column name error
   - Logic error
   - Syntax error
5. Add failed queries + correct SQL to the few-shot store for future improvement

Output JSON:
{
  "accuracy_score": 0.0 to 1.0,
  "result_match": true/false,
  "root_cause": "...",
  "recommendation": "..."
}
"""

GOLD_TEST_SUITE = [
    {
        "complexity": "SIMPLE",
        "question": "Show me all records from the first table",
        "note": "Replace with your actual test questions after data ingestion"
    },
    {
        "complexity": "MEDIUM",
        "question": "Count the total number of records per category",
        "note": "Replace with domain-specific test questions"
    },
    {
        "complexity": "HARD",
        "question": "Find the top 10 entries by value joining all three tables",
        "note": "Replace with domain-specific test questions"
    }
]


def compare_result_sets(rows_gold: list, rows_generated: list, ordered: bool = False) -> float:
    """Compare two result sets and return accuracy score."""
    if not rows_gold and not rows_generated:
        return 1.0
    if not rows_gold or not rows_generated:
        return 0.0

    try:
        if ordered:
            if len(rows_gold) != len(rows_generated):
                return 0.5 if len(rows_gold) > 0 else 0.0
            matches = sum(1 for a, b in zip(rows_gold, rows_generated)
                         if [str(x) for x in a] == [str(x) for x in b])
            return matches / len(rows_gold)
        else:
            set_gold = set(tuple(str(x) for x in r) for r in rows_gold)
            set_gen = set(tuple(str(x) for x in r) for r in rows_generated)
            if set_gold == set_gen:
                return 1.0
            intersection = len(set_gold & set_gen)
            union = len(set_gold | set_gen)
            return intersection / union if union > 0 else 0.0
    except Exception:
        return 0.0


def run_evaluation(conn_str: str, test_cases: List[dict], pipeline_fn) -> dict:
    """Run evaluation suite against the full pipeline."""
    results = []
    total_score = 0.0

    for test in test_cases:
        if "gold_sql" not in test:
            continue

        result = pipeline_fn(test["question"])
        gen_sql = result.get("sql", "")
        gen_rows = result.get("rows", [])

        # Run gold SQL
        try:
            conn = psycopg2.connect(conn_str)
            cur = conn.cursor()
            cur.execute(test["gold_sql"])
            gold_rows = [list(r) for r in cur.fetchall()]
            cur.close()
            conn.close()
        except Exception as e:
            gold_rows = []

        score = compare_result_sets(gold_rows, gen_rows)
        total_score += score

        results.append({
            "question": test["question"],
            "complexity": test.get("complexity", "UNKNOWN"),
            "gold_sql": test["gold_sql"],
            "generated_sql": gen_sql,
            "accuracy_score": score,
            "gold_row_count": len(gold_rows),
            "generated_row_count": len(gen_rows),
            "passed": score >= 0.95
        })

    avg_score = total_score / len(results) if results else 0.0
    passed = sum(1 for r in results if r["passed"])

    return {
        "total_tests": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "average_accuracy": round(avg_score, 4),
        "results": results
    }


def export_failures_for_finetuning(eval_results: dict, output_path: str):
    """Export failed cases as training data for fine-tuning."""
    failures = [r for r in eval_results["results"] if not r["passed"] and r["gold_sql"]]
    training_data = []
    for f in failures:
        training_data.append({
            "messages": [
                {"role": "user", "content": f["question"]},
                {"role": "assistant", "content": f["gold_sql"]}
            ],
            "complexity": f["complexity"],
            "accuracy_score": f["accuracy_score"]
        })
    with open(output_path, "w") as fp:
        json.dump(training_data, fp, indent=2)
    return len(training_data)


def add_failure_to_examples(
    conn_str: str,
    question: str,
    correct_sql: str,
    complexity: str,
    embedder=None
):
    """Add a corrected query back into the few-shot store (feedback loop)."""
    from core.phase2_embeddings import get_ollama_embedding
    emb = get_ollama_embedding(question)
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO nl_sql_pairs (intent, question, sql_query, question_embedding)
           VALUES (%s, %s, %s, %s)""",
        (complexity, question, correct_sql, emb)
    )
    conn.commit()
    cur.close()
    conn.close()


def get_accuracy_report(conn_str: str) -> dict:
    """Get accuracy stats from query history."""
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()
        cur.execute("""
            SELECT
                complexity,
                COUNT(*) as total,
                SUM(CASE WHEN was_valid THEN 1 ELSE 0 END) as passed,
                AVG(execution_time_ms) as avg_ms,
                SUM(CASE WHEN feedback = 1 THEN 1 ELSE 0 END) as thumbs_up,
                SUM(CASE WHEN feedback = -1 THEN 1 ELSE 0 END) as thumbs_down
            FROM nlpsql_query_history
            GROUP BY complexity
            ORDER BY complexity
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        report = {}
        for r in rows:
            report[r[0]] = {
                "total": r[1],
                "passed": r[2],
                "accuracy": round(r[2] / r[1], 3) if r[1] > 0 else 0,
                "avg_ms": round(r[3] or 0, 1),
                "thumbs_up": r[4],
                "thumbs_down": r[5]
            }
        return report
    except Exception:
        return {}
