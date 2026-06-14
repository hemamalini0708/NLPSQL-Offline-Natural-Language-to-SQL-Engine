import sys
import io
import json
import asyncio
import logging
import queue
import threading
from typing import List, Optional, Dict, Any, Generator
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pathlib import Path

# Import our core modules
from core.phase6_orchestrator import run_pipeline, get_query_history, save_feedback
from core.phase1_ingestion import analyze_csv, save_schema_metadata
from core.phase2_embeddings import (
    setup_pgvector, embed_and_store_schema
)
from core.phase7_evaluation import get_accuracy_report
from config import DB_URL, LLM_MODEL

# Configure FastAPI
app = FastAPI(title="NLPSQL API")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---
class QueryRequest(BaseModel):
    question: str
    model: Optional[str] = LLM_MODEL
    conn_str: Optional[str] = DB_URL

class FeedbackRequest(BaseModel):
    query_id: int
    feedback: int

# --- Real-time Log Capture ---
class LogQueue(io.TextIOBase):
    def __init__(self):
        self.queue = queue.Queue()
    def write(self, s):
        if s.strip():
            self.queue.put(s.strip())
        return len(s)
    def get_logs(self):
        while not self.queue.empty():
            yield self.queue.get()

# --- Endpoints ---

@app.get("/api/status")
def get_status():
    schema_path = Path("data/schema_metadata.json")
    schema_loaded = schema_path.exists()
    tables = []
    if schema_loaded:
        try:
            with open(schema_path) as f:
                meta = json.load(f)
                tables = [t["table_name"] for t in meta.get("tables", [])]
        except: pass
    
    return {
        "status": "online",
        "schema_loaded": schema_loaded,
        "tables": tables,
        "model": LLM_MODEL
    }

@app.post("/api/query")
def execute_query(req: QueryRequest):
    # Use standard def so FastAPI runs it in a threadpool, preventing server blocking
    try:
        # Redirect stdout temporarily to capture logs for the response (non-streaming fallback)
        stdout_orig = sys.stdout
        sys.stdout = io.StringIO()
        
        result = run_pipeline(
            question=req.question,
            conn_str=req.conn_str,
            model=req.model
        )
        
        logs = sys.stdout.getvalue().splitlines()
        sys.stdout = stdout_orig
        
        return {
            "result": result,
            "logs": logs
        }
    except Exception as e:
        sys.stdout = stdout_orig
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/query/stream")
async def stream_query(question: str):
    """Streaming endpoint for real-time log visualization."""
    log_q = LogQueue()
    
    def run_and_capture():
        stdout_orig = sys.stdout
        sys.stdout = log_q
        try:
            print(f"--- Starting Pipeline for: {question} ---")
            result = run_pipeline(question=question, conn_str=DB_URL, model=LLM_MODEL)
            
            # Use a custom encoder to handle non-serializable types like datetime.date and Decimal
            def json_serial(obj):
                from datetime import date, datetime
                from decimal import Decimal
                if isinstance(obj, (date, datetime)):
                    return obj.isoformat()
                if isinstance(obj, Decimal):
                    return float(obj)
                return str(obj)

            # Send the final result as a special JSON log line
            print(f"RESULT_JSON:{json.dumps(result, default=json_serial)}")
        except Exception as e:
            print(f"[ERROR] {str(e)}")
        finally:
            sys.stdout = stdout_orig
            log_q.queue.put("DONE")

    threading.Thread(target=run_and_capture).start()

    async def event_generator():
        while True:
            await asyncio.sleep(0.1)
            try:
                line = log_q.queue.get_nowait()
                if line == "DONE":
                    yield "event: DONE\ndata: ok\n\n"
                    break
                yield f"data: {line}\n\n"
            except queue.Empty:
                continue

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/history")
def get_history(limit: int = 50):
    return get_query_history(DB_URL, limit=limit)

@app.post("/api/feedback")
def post_feedback(req: FeedbackRequest):
    save_feedback(DB_URL, req.query_id, req.feedback)
    return {"status": "success"}

@app.get("/api/evaluation")
def get_evaluation():
    return get_accuracy_report(DB_URL)

@app.post("/api/setup/initialize")
def initialize_system(conn_str: Optional[str] = DB_URL):
    try:
        setup_pgvector(conn_str)
        schema_path = Path("data/schema_metadata.json")
        if not schema_path.exists():
            return {"success": False, "error": "No schema metadata found."}
        
        with open(schema_path) as f:
            meta = json.load(f)
        
        count = embed_and_store_schema(meta, conn_str)
        return {"success": True, "embedded_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
