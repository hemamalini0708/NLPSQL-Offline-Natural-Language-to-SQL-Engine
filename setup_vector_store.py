import json
import os
from config import DB_URL, EMBED_MODEL
from core.phase2_embeddings import setup_pgvector, embed_and_store_schema, get_local_embedder

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    metadata_path = os.path.join(base_dir, "data", "schema_metadata.json")
    
    if not os.path.exists(metadata_path):
        print("Error: schema_metadata.json not found. Run generate_metadata.py first.")
        return

    with open(metadata_path, "r") as f:
        meta = json.load(f)

    print("Setting up pgvector...")
    setup_pgvector(DB_URL)

    print(f"Embedding schema using {EMBED_MODEL}...")
    embedder = get_local_embedder()
    count = embed_and_store_schema(meta, DB_URL, embedder)
    print(f"Successfully embedded {count} schema fragments.")

if __name__ == "__main__":
    main()
