import psycopg2
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

def verify():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        for tbl in ['customers', 'orders', 'payments', 'nl_sql_pairs']:
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            print(f"{tbl}: {cur.fetchone()[0]} rows")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify()
