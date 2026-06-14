import json
import os
from config import DB_URL
from core.phase2_embeddings import setup_pgvector, embed_and_store_examples

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    seed_path = os.path.join(base_dir, "seed_pairs.json")
    
    if not os.path.exists(seed_path):
        print(f"Error: {seed_path} not found.")
        return

    with open(seed_path, "r") as f:
        examples = json.load(f)

    print(f"Loading {len(examples)} examples into vector store...")
    setup_pgvector(DB_URL)
    count = embed_and_store_examples(examples, DB_URL)
    print(f"Successfully embedded {count} examples.")

if __name__ == "__main__":
    main()
