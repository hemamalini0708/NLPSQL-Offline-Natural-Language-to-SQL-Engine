# 🧠 NLPSQL — Offline Natural Language to SQL Engine

> **Ask questions in plain English. Get SQL instantly. No cloud. No API keys. 100% offline.**

NLPSQL is a production-grade, fully offline AI system that converts natural language questions into executable PostgreSQL queries using a local LLM, vector-based RAG retrieval, and a self-healing pipeline — all running on your own machine.

---

## ✨ What Makes This Special

| Feature | Description |
|---|---|
| 🔒 **Fully Offline** | Runs entirely on localhost — no OpenAI, no cloud LLM calls |
| 🧠 **RAG-Powered** | Retrieves relevant schema + few-shot examples via pgvector cosine search |
| 🔁 **Self-Healing SQL** | Automatically detects and repairs broken queries using LLM feedback |
| 🧭 **Complexity Router** | Classifies queries (SIMPLE → ULTRA) and scales retrieval accordingly |
| 📊 **Full Streamlit UI** | Query, History, Evaluation, and Setup tabs in one polished interface |
| 🗂️ **Query History** | Every query logged with SQL, complexity, execution time, row count |
| ⭐ **Feedback System** | Thumbs up/down per query for continuous improvement tracking |
| 📈 **Accuracy Metrics** | Evaluation dashboard grouped by complexity level |

---

## 🏗️ Architecture — 7-Phase Pipeline

```
Natural Language Question
         │
         ▼
┌─────────────────────┐
│  Phase 5 — Router   │  Classifies complexity: SIMPLE / MEDIUM / HARD / ADVANCED / ULTRA
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Phase 2 — RAG      │  Retrieves schema fragments + few-shot examples via pgvector
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Phase 3 — LLM Core │  Generates SQL using Ollama (local LLM)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Phase 4 — Validator│  Syntax + safety check via sqlglot
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Phase 6 — Execute  │  Runs query on PostgreSQL, self-heals on error
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Phase 7 — Evaluate │  Logs to history, computes accuracy metrics
└─────────────────────┘
```

---

## 🗄️ Database Schema

Three interconnected tables across a realistic e-commerce domain:

- **customers** — 15 columns: demographics, loyalty score, income, account status
- **orders** — 15 columns: products, pricing, discounts, shipping, delivery dates
- **payments** — 15 columns: gateway, fraud flags, refunds, installments, device type

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **UI** | Streamlit |
| **LLM** | Ollama (local) — `llama3`, `qwen2.5-coder`, `sqlcoder` |
| **Embeddings** | SentenceTransformers (`all-MiniLM-L6-v2`) |
| **Vector Store** | PostgreSQL + pgvector (cosine similarity + HNSW index) |
| **SQL Validation** | sqlglot |
| **Database** | PostgreSQL 15+ (via pgAdmin 4) |
| **Backend API** | FastAPI + Uvicorn (optional REST layer) |
| **DB Driver** | psycopg2, SQLAlchemy |
| **Language** | Python 3.11 |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL with pgvector extension
- Ollama installed and running (`ollama serve`)

### 1. Clone & Install
```bash
git clone https://github.com/hemamalini0708/NLPSQL-Offline-Natural-Language-to-SQL-Engine.git
cd NLPSQL-Offline-Natural-Language-to-SQL-Engine
pip install -r requirements.txt
```

### 2. Configure Environment
Create a `.env` file:
```
DB_URL=postgresql://postgres:yourpassword@localhost:5432/vectordb
LLM_MODEL=llama3
EMBED_MODEL=all-MiniLM-L6-v2
EMBED_DIM=384
TOP_K=5
```

### 3. Setup Database
```bash
python setup_db.py           # Creates schema + loads CSV data
python generate_metadata.py  # Analyzes CSVs → schema_metadata.json
python setup_vector_store.py # Embeds schema into pgvector
python load_examples.py      # Embeds few-shot NL→SQL pairs
```

### 4. Pull LLM Model
```bash
ollama pull llama3
```

### 5. Launch
```bash
streamlit run app.py
```
Or double-click `launch.bat` on Windows.

---

## 📁 Project Structure

```
nlpsql/
├── core/
│   ├── phase1_ingestion.py     # CSV schema analysis
│   ├── phase2_embeddings.py    # SentenceTransformers + pgvector
│   ├── phase3_llm_core.py      # Ollama LLM SQL generation + self-healing
│   ├── phase4_validator.py     # sqlglot syntax + safety validation
│   ├── phase5_router.py        # Query complexity classification
│   ├── phase6_orchestrator.py  # Full pipeline + history logging
│   └── phase7_evaluation.py    # Accuracy metrics
├── data/
│   └── schema_metadata.json    # Auto-generated schema context
├── app.py                      # Streamlit UI
├── main.py                     # FastAPI REST backend
├── setup_db.py                 # DB init + CSV loader
├── generate_metadata.py        # Schema analysis runner
├── setup_vector_store.py       # Embedding pipeline runner
├── load_examples.py            # Few-shot examples loader
├── schema.sql                  # PostgreSQL DDL
├── seed_pairs.json             # Few-shot NL→SQL training pairs
└── requirements.txt
```

---

## 💡 Example Queries

```
"show all customers from Mumbai"
"monthly trend of total sales in 2024"
"rank customers by total revenue in New York"
"find customers who spent more than 5000"
"show fraud flagged payments with refund amount greater than 1000"
```

---

## 📊 Key Pipeline Features

**Self-Healing** — When a query fails, the LLM receives the PostgreSQL error and auto-generates a corrected query (up to 2 retries).

**RAG Retrieval** — Schema and few-shot examples are embedded and retrieved by cosine similarity so the LLM always gets the most relevant context.

**Complexity Routing** — Queries are classified before retrieval, scaling `TOP_K` dynamically so harder queries get richer context.

---

## 🔧 Skills Demonstrated

`Python` · `PostgreSQL` · `pgvector` · `Vector Databases` · `RAG` · `LLM Integration` · `Ollama` · `SentenceTransformers` · `Streamlit` · `FastAPI` · `NLP` · `SQL Generation` · `sqlglot` · `psycopg2` · `Multi-phase Pipeline Architecture` · `System Design`

---

## 👩‍💻 Author

**Hema Malini** · [GitHub @hemamalini0708](https://github.com/hemamalini0708)

---

*Built as a showcase of offline AI engineering — combining local LLMs, semantic search, and production-grade pipeline design without any cloud dependency.*
