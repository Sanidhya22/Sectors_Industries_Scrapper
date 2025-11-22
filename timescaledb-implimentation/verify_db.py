from database_config import get_db_connection


def verify_data():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT count(*) FROM stock_prices;")
        count = cur.fetchone()[0]
        print(f"Total rows in stock_prices: {count}")

        cur.execute("SELECT * FROM stock_prices LIMIT 5;")
        rows = cur.fetchall()
        print("Sample data:")
        for row in rows:
            print(row)

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Verification failed: {e}")


if __name__ == "__main__":
    verify_data()
