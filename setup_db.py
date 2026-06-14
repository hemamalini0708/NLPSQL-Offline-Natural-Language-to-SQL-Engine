import psycopg2
import os
import csv
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

def setup_database():
    """Initializes the database schema and loads CSV data."""
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.autocommit = True
        cur = conn.cursor()

        print("--- Initializing Schema ---")
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, "r") as f:
            cur.execute(f.read())
        print("Schema initialized successfully.")

        # Load CSV data
        tables = {
            "customers": "customers.csv",
            "orders": "orders.csv",
            "payments": "payments.csv"
        }

        for table, csv_file in tables.items():
            csv_path = os.path.join(os.path.dirname(__file__), csv_file)
            if not os.path.exists(csv_path):
                print(f"Warning: {csv_file} not found. Skipping.")
                continue

            print(f"--- Loading {csv_file} into {table} ---")
            
            # Using COPY for high performance
            with open(csv_path, "r") as f:
                # Get the header to ensure columns match
                reader = csv.reader(f)
                header = next(reader)
                cols = ",".join(header)
                
                f.seek(0)
                next(f) # Skip header
                cur.copy_expert(f"COPY {table} ({cols}) FROM STDIN WITH CSV", f)
            
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"Successfully loaded {count} rows into {table}.")

        cur.close()
        conn.close()
        print("--- Database Setup Complete ---")

    except Exception as e:
        print(f"Error during database setup: {e}")

if __name__ == "__main__":
    setup_database()
