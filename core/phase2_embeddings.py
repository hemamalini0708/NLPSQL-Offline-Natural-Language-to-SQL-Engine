"""
NLPSQL SYSTEM — PHASE 02
Offline Embedding & Vector Store (pgvector via Ollama)
Modified to support 768-dim vectors and Ollama local API.
"""

import json
import psycopg2
import requests
from typing import List, Optional
from config import EMBED_MODEL, EMBED_DIM

def get_ollama_embedding(text: str) -> List[float]:
    """Get embedding from local Ollama API."""
    try:
        response = requests.post(
            "http://localhost:11434/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=10
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except Exception as e:
        print(f"Error calling Ollama embedding API: {e}")
        # Return dummy vector if it fails (not ideal, but prevents crash)
        return [0.0] * EMBED_DIM

def setup_pgvector(conn_str: str):
    """Initializes pgvector tables."""
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()

    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Table for schema embeddings
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS nlpsql_schema_embeddings (
            id SERIAL PRIMARY KEY,
            table_name TEXT NOT NULL,
            column_name TEXT,
            description TEXT NOT NULL,
            embedding vector({EMBED_DIM}),
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    # Table for training examples (if not exists)
    # We use nl_sql_pairs as the primary source, but this can be a mirror or cache
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS nl_sql_pairs (
            id SERIAL PRIMARY KEY,
            question TEXT NOT NULL,
            sql_query TEXT NOT NULL,
            intent VARCHAR,
            question_embedding vector({EMBED_DIM}),
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_schema_embed ON nlpsql_schema_embeddings USING hnsw (embedding vector_cosine_ops);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pairs_embed ON nl_sql_pairs USING hnsw (question_embedding vector_cosine_ops);")

    conn.commit()
    cur.close()
    conn.close()

def embed_and_store_schema(schema_metadata: dict, conn_str: str, embedder=None):
    """Embeds schema fragments and stores in DB."""
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()

    count = 0
    for table in schema_metadata["tables"]:
        # Table level
        table_desc = f"Table {table['table_name']}: {table.get('description', '')}. Contains {table['total_rows']:,} records."
        emb = get_ollama_embedding(table_desc)
        cur.execute(
            "INSERT INTO nlpsql_schema_embeddings (table_name, column_name, description, embedding, metadata) VALUES (%s, %s, %s, %s, %s)",
            (table["table_name"], None, table_desc, emb, json.dumps({"type": "table"}))
        )
        count += 1

        # Column level
        for col in table["columns"]:
            col_desc = f"Column {col['clean_name']} in table {table['table_name']}: {col.get('description', '')}. Type: {col['pg_type']}."
            emb = get_ollama_embedding(col_desc)
            cur.execute(
                "INSERT INTO nlpsql_schema_embeddings (table_name, column_name, description, embedding, metadata) VALUES (%s, %s, %s, %s, %s)",
                (table["table_name"], col["clean_name"], col_desc, emb, json.dumps({"type": "column"}))
            )
            count += 1

    conn.commit()
    cur.close()
    conn.close()
    return count

def retrieve_similar_schema(question: str, conn_str: str, embedder=None, top_k: int = 8) -> List[dict]:
    emb = get_ollama_embedding(question)
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    cur.execute(
        f"SELECT table_name, column_name, description, 1 - (embedding <=> %s::vector) AS similarity FROM nlpsql_schema_embeddings ORDER BY embedding <=> %s::vector LIMIT %s",
        (emb, emb, top_k)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"table": r[0], "column": r[1], "description": r[2], "similarity": float(r[3])} for r in rows]

def retrieve_similar_examples(question: str, conn_str: str, embedder=None, top_k: int = 5) -> List[dict]:
    emb = get_ollama_embedding(question)
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    cur.execute(
        f"SELECT question, sql_query, intent, 1 - (question_embedding <=> %s::vector) AS similarity FROM nl_sql_pairs ORDER BY question_embedding <=> %s::vector LIMIT %s",
        (emb, emb, top_k)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"question": r[0], "sql": r[1], "complexity": r[2] or "GENERAL", "similarity": float(r[3])} for r in rows]

def get_local_embedder():
    """Placeholder to maintain API compatibility."""
    return None

def embed_texts(texts: List[str], embedder=None) -> List[List[float]]:
    """Helper to embed a list of strings."""
    return [get_ollama_embedding(t) for t in texts]

def embed_and_store_examples(examples: List[dict], conn_str: str):
    """
    Embeds natural language questions from few-shot examples and stores them in DB.
    Expected format for each example: {"question": "...", "sql": "...", "complexity": "..."}
    """
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()

    count = 0
    for ex in examples:
        emb = get_ollama_embedding(ex["question"])
        cur.execute(
            "INSERT INTO nl_sql_pairs (question, sql_query, intent, question_embedding) VALUES (%s, %s, %s, %s)",
            (ex["question"], ex["sql"], ex.get("complexity", "GENERAL"), emb)
        )
        count += 1

    conn.commit()
    cur.close()
    conn.close()
    return count
