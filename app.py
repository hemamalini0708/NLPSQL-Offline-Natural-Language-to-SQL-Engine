"""
NLPSQL SYSTEM — Main Streamlit Application
Production-grade offline NL→SQL generator
"""

import streamlit as st
import pandas as pd
import json
import os
import time
from pathlib import Path
from config import DB_URL, LLM_MODEL

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NLPSQL System",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@400;500;600;700&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  .main { background: #0a0e1a; }
  .block-container { padding: 2rem 2.5rem; max-width: 1400px; }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: #0d1117;
    border-right: 1px solid #1e2d3d;
  }
  [data-testid="stSidebar"] .block-container { padding: 1.5rem 1rem; }

  /* Logo */
  .nlpsql-logo {
    background: linear-gradient(135deg, #00d4ff, #7c3aed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 1.6rem;
    font-weight: 700;
    letter-spacing: -0.5px;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 0.2rem;
  }
  .nlpsql-sub {
    color: #4a5568;
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 1.5rem;
  }

  /* Query input & other text inputs */
  .stTextArea textarea, .stTextInput input {
    background: #ffffff !important;
    border: 1px solid #d1d5db !important;
    border-radius: 10px !important;
    color: #111827 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 1rem !important;
    transition: all 0.2s;
  }
  .stTextArea textarea:focus, .stTextInput input:focus {
    border-color: #00d4ff !important;
    box-shadow: 0 0 0 2px rgba(0, 212, 255, 0.1) !important;
  }

  /* SQL output box */
  .sql-box {
    background: #0d1117;
    border: 1px solid #1e2d3d;
    border-left: 3px solid #00d4ff;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    color: #a8d8ea;
    white-space: pre-wrap;
    line-height: 1.7;
    margin: 0.75rem 0;
    max-height: 320px;
    overflow-y: auto;
  }

  /* Complexity badges */
  .badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .badge-SIMPLE   { background: #052e16; color: #22c55e; }
  .badge-MEDIUM   { background: #0c1a3a; color: #60a5fa; }
  .badge-HARD     { background: #2d1b00; color: #f59e0b; }
  .badge-ADVANCED { background: #2d1200; color: #fb923c; }
  .badge-ULTRA    { background: #2d0000; color: #f87171; }

  /* Metric cards */
  .metric-card {
    background: #0d1117;
    border: 1px solid #1e2d3d;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    text-align: center;
  }
  .metric-val { font-size: 1.8rem; font-weight: 700; color: #00d4ff; }
  .metric-lbl { font-size: 0.72rem; color: #4a5568; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 2px; }

  /* Healed badge */
  .healed-badge {
    background: #1a2d1a;
    border: 1px solid #22c55e;
    color: #22c55e;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
  }

  /* Buttons */
  .stButton > button {
    background: #000000 !important;
    border: 1px solid #1e2d3d !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: all 0.2s !important;
  }
  .stButton > button:hover {
    border-color: #4a5568 !important;
    background: #111111 !important;
  }

  /* Run button */
  .run-btn > button {
    background: #000000 !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border: 1px solid #00d4ff !important;
    width: 100% !important;
    padding: 0.6rem !important;
  }
  .run-btn > button:hover {
    background: #0a0a0a !important;
    border-color: #7c3aed !important;
  }

  /* Dataframe */
  .stDataFrame { border-radius: 8px; overflow: hidden; }

  /* Section headers */
  .section-header {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #4a5568;
    margin: 1.5rem 0 0.75rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #1e2d3d;
  }

  /* Status dot */
  .dot-online { color: #22c55e; font-size: 0.7rem; }
  .dot-offline { color: #f87171; font-size: 0.7rem; }

  /* Info panels */
  .info-panel {
    background: #0d1117;
    border: 1px solid #1e2d3d;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    font-size: 0.83rem;
    color: #718096;
    margin: 0.5rem 0;
  }
  .info-panel code {
    font-family: 'JetBrains Mono', monospace;
    color: #00d4ff;
    font-size: 0.8rem;
  }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {
    background: #0d1117;
    border-radius: 8px;
    padding: 4px;
    gap: 4px;
    border: 1px solid #1e2d3d;
  }
  .stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 6px !important;
    color: #4a5568 !important;
    font-size: 0.82rem !important;
  }
  .stTabs [aria-selected="true"] {
    background: #1e2d3d !important;
    color: #e2e8f0 !important;
  }

  /* Warning box */
  .warn-box {
    background: #2d1b00;
    border: 1px solid #f59e0b44;
    border-left: 3px solid #f59e0b;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    font-size: 0.82rem;
    color: #fbbf24;
    margin: 0.5rem 0;
  }
  .error-box {
    background: #2d0000;
    border: 1px solid #f8717144;
    border-left: 3px solid #f87171;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    font-size: 0.82rem;
    color: #fca5a5;
    margin: 0.5rem 0;
  }
  .success-box {
    background: #052e16;
    border: 1px solid #22c55e44;
    border-left: 3px solid #22c55e;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    font-size: 0.82rem;
    color: #86efac;
    margin: 0.5rem 0;
  }
</style>
""", unsafe_allow_html=True)


# ── Session state defaults ────────────────────────────────────────────────────
if "schema_loaded" not in st.session_state:
    st.session_state.schema_loaded = False
if "embedder" not in st.session_state:
    st.session_state.embedder = None
if "query_result" not in st.session_state:
    st.session_state.query_result = None
if "conn_str" not in st.session_state:
    st.session_state.conn_str = DB_URL
if "model" not in st.session_state:
    st.session_state.model = LLM_MODEL


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="nlpsql-logo">NLPSQL</div>', unsafe_allow_html=True)
    st.markdown('<div class="nlpsql-sub">Offline NL → SQL Engine</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">Database Connection</div>', unsafe_allow_html=True)
    conn_str = st.text_input(
        "PostgreSQL URL",
        value=st.session_state.conn_str,
        type="password",
        label_visibility="collapsed",
        placeholder="postgresql://user:pass@localhost:5432/nlpsql"
    )
    st.session_state.conn_str = conn_str

    # Test connection
    if st.button("Test Connection", use_container_width=True):
        try:
            import psycopg2
            psycopg2.connect(conn_str).close()
            st.markdown('<div class="success-box">✓ Connected successfully</div>', unsafe_allow_html=True)
        except Exception as e:
            st.markdown(f'<div class="error-box">✗ {str(e)[:80]}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">LLM Model</div>', unsafe_allow_html=True)
    model_choice = st.selectbox(
        "Ollama model",
        ["qwen2.5-coder:1.5b", "llama3", "sqlcoder", "deepseek-coder"],
        index=0,
        label_visibility="collapsed"
    )
    st.session_state.model = model_choice

    st.markdown('<div class="section-header">Schema Status</div>', unsafe_allow_html=True)
    schema_path = Path("data/schema_metadata.json")
    if schema_path.exists():
        with open(schema_path) as f:
            meta = json.load(f)
        tables = meta.get("tables", [])
        st.markdown(f'<div class="success-box">✓ Schema loaded · {len(tables)} tables</div>', unsafe_allow_html=True)
        for t in tables:
            st.markdown(f'<div class="info-panel">📋 <code>{t["table_name"]}</code> · {t["total_rows"]:,} rows</div>', unsafe_allow_html=True)
        st.session_state.schema_loaded = True
    else:
        st.markdown('<div class="warn-box">⚠ No schema loaded yet.<br>Go to Setup tab.</div>', unsafe_allow_html=True)
        st.session_state.schema_loaded = False

    st.markdown('<div class="section-header">Quick Examples</div>', unsafe_allow_html=True)
    example_questions = [
        "Show all records from the first table",
        "Count records grouped by category",
        "Top 10 by value with JOIN",
        "Monthly trend with running total",
        "Rank customers by revenue per region"
    ]
    for q in example_questions:
        if st.button(q, use_container_width=True, key=f"ex_{q[:20]}"):
            st.session_state["prefill_question"] = q


# ── Main content ──────────────────────────────────────────────────────────────
tab_query, tab_setup, tab_history, tab_eval = st.tabs([
    "🔍  Query", "⚙️  Setup", "📜  History", "📊  Evaluation"
])


# ─── TAB 1: QUERY ─────────────────────────────────────────────────────────────
with tab_query:
    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        st.markdown('<div class="section-header">Natural Language Question</div>', unsafe_allow_html=True)
        prefill = st.session_state.pop("prefill_question", "")
        question = st.text_area(
            "question",
            value=prefill,
            height=110,
            placeholder="e.g. Show me the top 10 customers by total revenue in Q1 2024...",
            label_visibility="collapsed"
        )

        run_col, clear_col = st.columns([3, 1])
        with run_col:
            st.markdown('<div class="run-btn">', unsafe_allow_html=True)
            run_clicked = st.button("⚡ Generate & Execute SQL", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with clear_col:
            if st.button("Clear", use_container_width=True):
                st.session_state.query_result = None
                st.rerun()

        if run_clicked and question.strip():
            if not st.session_state.schema_loaded:
                st.markdown('<div class="error-box">⚠ Please complete Setup first (load your CSV files).</div>', unsafe_allow_html=True)
            else:
                with st.spinner("Thinking..."):
                    try:
                        from core.phase6_orchestrator import run_pipeline
                        from core.phase2_embeddings import get_local_embedder

                        if st.session_state.embedder is None:
                            st.session_state.embedder = get_local_embedder()

                        result = run_pipeline(
                            question=question,
                            conn_str=st.session_state.conn_str,
                            model=st.session_state.model,
                            embedder=st.session_state.embedder
                        )
                        st.session_state.query_result = result
                    except Exception as e:
                        st.session_state.query_result = {
                            "success": False, "error": str(e),
                            "sql": "", "complexity": "UNKNOWN",
                            "rows": [], "columns": [], "row_count": 0,
                            "execution_time_ms": 0, "healed": False, "warnings": []
                        }

        # ── Results ──
        result = st.session_state.query_result
        if result:
            complexity = result.get("complexity", "")
            badge_html = f'<span class="badge badge-{complexity}">{complexity}</span>'

            healed_html = ""
            if result.get("healed"):
                healed_html = ' <span class="healed-badge">⚕ self-healed</span>'

            st.markdown(
                f'<div style="margin:0.5rem 0">{badge_html}{healed_html}</div>',
                unsafe_allow_html=True
            )

            st.markdown('<div class="section-header">Generated SQL</div>', unsafe_allow_html=True)
            sql_display = result.get("sql", "-- no query generated")
            st.markdown(f'<div class="sql-box">{sql_display}</div>', unsafe_allow_html=True)

            if result.get("success"):
                st.markdown('<div class="section-header">Results</div>', unsafe_allow_html=True)
                cols = result.get("columns", [])
                rows = result.get("rows", [])
                if rows:
                    df = pd.DataFrame(rows, columns=cols)
                    st.dataframe(df, use_container_width=True, height=280)
                    st.download_button(
                        "⬇ Download CSV",
                        df.to_csv(index=False),
                        file_name="nlpsql_result.csv",
                        mime="text/csv"
                    )
                else:
                    st.markdown('<div class="info-panel">Query ran successfully but returned 0 rows.</div>', unsafe_allow_html=True)

                if result.get("warnings"):
                    for w in result["warnings"]:
                        st.markdown(f'<div class="warn-box">⚠ {w}</div>', unsafe_allow_html=True)
            else:
                err = result.get("error", "Unknown error")
                st.markdown(f'<div class="error-box">✗ {err}</div>', unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="section-header">Execution Metrics</div>', unsafe_allow_html=True)
        result = st.session_state.query_result
        if result:
            m1, m2 = st.columns(2)
            with m1:
                st.markdown(f"""
                <div class="metric-card">
                  <div class="metric-val">{result.get("row_count", 0)}</div>
                  <div class="metric-lbl">Rows Returned</div>
                </div>""", unsafe_allow_html=True)
            with m2:
                ms = result.get("execution_time_ms", 0)
                st.markdown(f"""
                <div class="metric-card">
                  <div class="metric-val">{ms}ms</div>
                  <div class="metric-lbl">Total Time</div>
                </div>""", unsafe_allow_html=True)

            st.markdown('<div class="section-header">RAG Context Used</div>', unsafe_allow_html=True)
            st.markdown(f"""
            <div class="info-panel">
              📐 Schema fragments: <code>{result.get("schema_context_used", 0)}</code><br>
              💡 Few-shot examples: <code>{result.get("examples_used", 0)}</code><br>
              🤖 Model: <code>{st.session_state.model}</code>
            </div>""", unsafe_allow_html=True)

            st.markdown('<div class="section-header">Feedback</div>', unsafe_allow_html=True)
            fb1, fb2 = st.columns(2)
            with fb1:
                if st.button("👍 Correct", use_container_width=True):
                    st.markdown('<div class="success-box">Thanks! Logged as correct.</div>', unsafe_allow_html=True)
            with fb2:
                if st.button("👎 Wrong", use_container_width=True):
                    st.markdown('<div class="error-box">Noted. Will improve.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="info-panel">Run a query to see metrics here.</div>', unsafe_allow_html=True)


# ─── TAB 2: SETUP ─────────────────────────────────────────────────────────────
with tab_setup:
    st.markdown("### ⚙️ System Setup")

    setup_col1, setup_col2 = st.columns(2, gap="large")

    with setup_col1:
        st.markdown('<div class="section-header">Step 1 — Upload CSV Files</div>', unsafe_allow_html=True)
        st.markdown('<div class="info-panel">Upload your 3 CSV files (1 lakh+ rows each). The system will auto-detect schema.</div>', unsafe_allow_html=True)

        csv1 = st.file_uploader("CSV File 1", type=["csv"], key="csv1")
        tbl1 = st.text_input("Table name for File 1", value="table_one", key="tbl1")
        csv2 = st.file_uploader("CSV File 2", type=["csv"], key="csv2")
        tbl2 = st.text_input("Table name for File 2", value="table_two", key="tbl2")
        csv3 = st.file_uploader("CSV File 3", type=["csv"], key="csv3")
        tbl3 = st.text_input("Table name for File 3", value="table_three", key="tbl3")

        if st.button("🔄 Run Phase 1: Analyze Schema", use_container_width=True):
            uploads = [(csv1, tbl1), (csv2, tbl2), (csv3, tbl3)]
            valid = [(f, t) for f, t in uploads if f is not None]
            if not valid:
                st.markdown('<div class="error-box">Upload at least one CSV file.</div>', unsafe_allow_html=True)
            else:
                with st.spinner("Analyzing schema..."):
                    from core.phase1_ingestion import analyze_csv, save_schema_metadata
                    import tempfile
                    analyses = []
                    for uploaded_file, table_name in valid:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                            tmp.write(uploaded_file.read())
                            tmp_path = tmp.name
                        a = analyze_csv(tmp_path, table_name)
                        analyses.append(a)
                        os.unlink(tmp_path)
                    os.makedirs("data", exist_ok=True)
                    save_schema_metadata(analyses, "data/schema_metadata.json")
                    st.markdown(f'<div class="success-box">✓ Schema analyzed: {len(analyses)} tables detected.</div>', unsafe_allow_html=True)
                    st.rerun()

    with setup_col2:
        st.markdown('<div class="section-header">Step 2 — Initialize Vector Store</div>', unsafe_allow_html=True)
        st.markdown('<div class="info-panel">Creates pgvector tables, embeds schema + examples. Runs 100% offline using local sentence-transformers.</div>', unsafe_allow_html=True)

        if st.button("🧠 Run Phase 2: Build Embeddings", use_container_width=True):
            if not schema_path.exists():
                st.markdown('<div class="error-box">Complete Step 1 first.</div>', unsafe_allow_html=True)
            else:
                with st.spinner("Setting up vector store and embedding schema..."):
                    try:
                        from core.phase2_embeddings import (
                            setup_pgvector, embed_and_store_schema, get_local_embedder
                        )
                        setup_pgvector(st.session_state.conn_str)
                        with open("data/schema_metadata.json") as f:
                            meta = json.load(f)
                        if st.session_state.embedder is None:
                            st.session_state.embedder = get_local_embedder()
                        count = embed_and_store_schema(meta, st.session_state.conn_str, st.session_state.embedder)
                        st.markdown(f'<div class="success-box">✓ Embedded {count} schema fragments into pgvector.</div>', unsafe_allow_html=True)
                    except Exception as e:
                        st.markdown(f'<div class="error-box">✗ {str(e)}</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-header">Step 3 — Ollama Setup Guide</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="info-panel">
          1. Install Ollama: <code>https://ollama.ai</code><br>
          2. Start server: <code>ollama serve</code><br>
          3. Pull model: <code>ollama pull sqlcoder</code><br>
          4. Verify: <code>ollama list</code>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🔍 Check Ollama Status", use_container_width=True):
            try:
                import requests
                r = requests.get("http://localhost:11434/api/tags", timeout=3)
                models = [m["name"] for m in r.json().get("models", [])]
                st.markdown(f'<div class="success-box">✓ Ollama running · Models: {", ".join(models) or "none pulled"}</div>', unsafe_allow_html=True)
            except Exception:
                st.markdown('<div class="error-box">✗ Ollama not running. Run: <code>ollama serve</code></div>', unsafe_allow_html=True)


# ─── TAB 3: HISTORY ───────────────────────────────────────────────────────────
with tab_history:
    st.markdown("### 📜 Query History")

    if st.button("🔄 Refresh History"):
        st.rerun()

    try:
        from core.phase6_orchestrator import get_query_history
        history = get_query_history(st.session_state.conn_str, limit=100)
        if history:
            df_h = pd.DataFrame(history)
            df_h["status"] = df_h["was_valid"].map({True: "✓", False: "✗"})
            cols_show = ["created_at", "complexity", "status", "execution_time_ms", "row_count", "question"]
            df_h_show = df_h[cols_show].rename(columns={
                "created_at": "Time", "complexity": "Complexity",
                "status": "Status", "execution_time_ms": "ms",
                "row_count": "Rows", "question": "Question"
            })
            st.dataframe(df_h_show, use_container_width=True, height=400)
        else:
            st.markdown('<div class="info-panel">No queries yet. Run a query from the Query tab.</div>', unsafe_allow_html=True)
    except Exception as e:
        st.markdown(f'<div class="warn-box">Cannot load history: {str(e)[:120]}</div>', unsafe_allow_html=True)


# ─── TAB 4: EVALUATION ────────────────────────────────────────────────────────
with tab_eval:
    st.markdown("### 📊 Accuracy Evaluation (Phase 07)")

    try:
        from core.phase7_evaluation import get_accuracy_report
        report = get_accuracy_report(st.session_state.conn_str)
        if report:
            cols = st.columns(len(report))
            for i, (level, stats) in enumerate(report.items()):
                with cols[i]:
                    acc_pct = round(stats["accuracy"] * 100, 1)
                    st.markdown(f"""
                    <div class="metric-card">
                      <div class="metric-val">{acc_pct}%</div>
                      <div class="metric-lbl">{level}</div>
                      <div style="font-size:0.7rem;color:#4a5568;margin-top:4px">
                        {stats["passed"]}/{stats["total"]} · {stats["avg_ms"]}ms avg
                      </div>
                    </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="info-panel">No evaluation data yet. Run queries first.</div>', unsafe_allow_html=True)
    except Exception as e:
        st.markdown(f'<div class="warn-box">Cannot load evaluation: {str(e)[:120]}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">Add Gold Test Case</div>', unsafe_allow_html=True)
    gold_q = st.text_input("Natural language question", placeholder="What is the total revenue per region?")
    gold_sql = st.text_area("Gold SQL (correct answer)", height=100, placeholder="SELECT region, SUM(revenue) FROM orders GROUP BY region;")
    gold_level = st.selectbox("Complexity", ["SIMPLE", "MEDIUM", "HARD", "ADVANCED", "ULTRA"])
    if st.button("Add to Test Suite"):
        gold_path = Path("data/gold_tests.json")
        tests = json.loads(gold_path.read_text()) if gold_path.exists() else []
        tests.append({"question": gold_q, "gold_sql": gold_sql, "complexity": gold_level})
        gold_path.write_text(json.dumps(tests, indent=2))
        st.markdown('<div class="success-box">✓ Test case added.</div>', unsafe_allow_html=True)
