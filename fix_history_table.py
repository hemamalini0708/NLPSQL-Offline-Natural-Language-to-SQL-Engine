import psycopg2
from config import DB_URL

def fix_table():
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        print("Dropping old table if exists...")
        cur.execute("DROP TABLE IF EXISTS nlpsql_query_history CASCADE")
        cur.execute("DROP TABLE IF EXISTS query_history CASCADE")
        
        print("Creating new nlpsql_query_history table...")
        cur.execute("""
            CREATE TABLE nlpsql_query_history (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL,
                generated_sql TEXT NOT NULL,
                complexity VARCHAR(50),
                was_valid BOOLEAN,
                execution_time_ms INTEGER,
                row_count INTEGER,
                error_message TEXT,
                feedback INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        print("Table fixed successfully!")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_table()
