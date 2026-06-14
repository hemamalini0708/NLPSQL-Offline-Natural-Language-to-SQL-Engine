import psycopg2
from config import DB_URL

def check_dims():
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        tables = ['nlpsql_schema_embeddings', 'nl_sql_pairs']
        for table in tables:
            print(f"Checking {table}...")
            cur.execute(f"""
                SELECT atttypmod 
                FROM pg_attribute 
                WHERE attrelid = '{table}'::regclass 
                AND attname = '{'embedding' if table == 'nlpsql_schema_embeddings' else 'question_embedding'}'
            """)
            res = cur.fetchone()
            if res:
                # atttypmod for vector(N) is N
                print(f"  Dimension in DB: {res[0]}")
            else:
                print(f"  Column not found in {table}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_dims()
