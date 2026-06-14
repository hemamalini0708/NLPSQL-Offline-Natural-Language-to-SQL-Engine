"""
NLPSQL SYSTEM — PHASE 01
Data Ingestion & Schema Intelligence
"""

import pandas as pd
import psycopg2
import json
import re
from pathlib import Path
from typing import Optional


SYSTEM_PROMPT_PHASE1 = """
You are a senior database architect specializing in PostgreSQL schema design for enterprise MNC systems.

I will provide you with:
1. Column names and sample data from CSV files
2. Summary statistics for each column

Your task:
- Infer the most appropriate PostgreSQL data type for each column
- Detect primary key candidates (unique, non-null integer or UUID-like columns)
- Detect potential foreign key relationships across tables
- Generate complete CREATE TABLE DDL with proper types, constraints, indexes
- Write a plain-English semantic description (1-2 sentences) for every column
- Suggest table-level descriptions explaining what each table represents

Rules:
- Use ONLY PostgreSQL-compatible types: TEXT, INTEGER, BIGINT, NUMERIC, BOOLEAN, DATE, TIMESTAMP, UUID, JSONB
- Add NOT NULL where appropriate based on null counts
- Add CREATE INDEX statements for columns likely used in WHERE/JOIN clauses
- Output as valid JSON with this structure:
  {
    "tables": [
      {
        "table_name": "...",
        "description": "...",
        "ddl": "CREATE TABLE ...",
        "columns": [
          {"name": "...", "type": "...", "description": "...", "is_pk": bool, "is_fk": bool, "fk_ref": "table.column or null"}
        ],
        "indexes": ["CREATE INDEX ..."]
      }
    ],
    "relationships": [
      {"from": "table.column", "to": "table.column", "type": "MANY_TO_ONE"}
    ]
  }
"""


def infer_pg_type(series: pd.Series) -> str:
    dtype = series.dtype
    sample = series.dropna().head(100)
    if dtype == "bool":
        return "BOOLEAN"
    if dtype in ["int32", "int64"]:
        return "BIGINT" if series.max() > 2_147_483_647 else "INTEGER"
    if dtype == "float64":
        return "NUMERIC(18,4)"
    if dtype == "object":
        try:
            pd.to_datetime(sample)
            return "TIMESTAMP"
        except Exception:
            pass
        max_len = sample.astype(str).str.len().max() if len(sample) > 0 else 255
        if max_len and max_len <= 50:
            return f"VARCHAR({max_len * 2})"
        return "TEXT"
    if "datetime" in str(dtype):
        return "TIMESTAMP"
    return "TEXT"


def analyze_csv(filepath: str, table_name: str) -> dict:
    df = pd.read_csv(filepath, nrows=200)
    full_df = pd.read_csv(filepath)
    total_rows = len(full_df)

    columns_meta = []
    for col in df.columns:
        clean_col = re.sub(r'[^a-zA-Z0-9_]', '_', col.strip().lower())
        pg_type = infer_pg_type(full_df[col])
        null_count = full_df[col].isnull().sum()
        unique_count = full_df[col].nunique()
        sample_vals = full_df[col].dropna().head(5).tolist()
        columns_meta.append({
            "original_name": col,
            "clean_name": clean_col,
            "pg_type": pg_type,
            "null_count": int(null_count),
            "unique_count": int(unique_count),
            "total_rows": int(total_rows),
            "sample_values": [str(v) for v in sample_vals],
            "is_likely_pk": bool(unique_count == total_rows and null_count == 0)
        })
    return {
        "table_name": table_name,
        "filepath": filepath,
        "total_rows": int(total_rows),
        "columns": columns_meta
    }


def build_llm_context(analysis: dict) -> str:
    lines = [f"Table: {analysis['table_name']} ({analysis['total_rows']:,} rows)\n"]
    for col in analysis["columns"]:
        lines.append(
            f"  Column: {col['clean_name']} | Type hint: {col['pg_type']} | "
            f"Nulls: {col['null_count']} | Unique: {col['unique_count']} | "
            f"Likely PK: {col['is_likely_pk']} | Samples: {col['sample_values']}"
        )
    return "\n".join(lines)


def generate_basic_ddl(analysis: dict) -> str:
    table = analysis["table_name"]
    cols = []
    for col in analysis["columns"]:
        null_str = "NOT NULL" if col["null_count"] == 0 else ""
        pk_str = "PRIMARY KEY" if col["is_likely_pk"] else ""
        col_def = f"  {col['clean_name']} {col['pg_type']} {null_str} {pk_str}".strip()
        cols.append(col_def)
    ddl = f"CREATE TABLE {table} (\n" + ",\n".join(cols) + "\n);"
    return ddl


def save_schema_metadata(analyses: list, output_path: str):
    schema = {"tables": []}
    for a in analyses:
        schema["tables"].append({
            "table_name": a["table_name"],
            "total_rows": a["total_rows"],
            "columns": a["columns"],
            "basic_ddl": generate_basic_ddl(a),
            "llm_context": build_llm_context(a)
        })
    with open(output_path, "w") as f:
        json.dump(schema, f, indent=2)
    return schema


def load_csv_to_postgres(filepath: str, table_name: str, conn_str: str):
    df = pd.read_csv(filepath)
    df.columns = [re.sub(r'[^a-zA-Z0-9_]', '_', c.strip().lower()) for c in df.columns]
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    cols = ", ".join(df.columns)
    placeholders = ", ".join(["%s"] * len(df.columns))
    insert_sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
    batch = [tuple(row) for row in df.itertuples(index=False, name=None)]
    cur.executemany(insert_sql, batch)
    conn.commit()
    cur.close()
    conn.close()
    return len(batch)
