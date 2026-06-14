import os
import json
from core.phase1_ingestion import analyze_csv, save_schema_metadata

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    csv_files = {
        "customers": "customers.csv",
        "orders": "orders.csv",
        "payments": "payments.csv"
    }

    analyses = []
    for table, csv_file in csv_files.items():
        csv_path = os.path.join(base_dir, csv_file)
        if os.path.exists(csv_path):
            print(f"Analyzing {table}...")
            analysis = analyze_csv(csv_path, table)
            analyses.append(analysis)
        else:
            print(f"Warning: {csv_file} not found.")

    if analyses:
        output_path = os.path.join(data_dir, "schema_metadata.json")
        save_schema_metadata(analyses, output_path)
        print(f"Metadata saved to {output_path}")

if __name__ == "__main__":
    main()
