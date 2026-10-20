
import sqlite3
from pathlib import Path

# Project root se database ka correct path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "database" / "company.db"


def view_database():
    print(f"Database path: {DB_PATH}")

    if not DB_PATH.exists():
        print("ERROR: Database file nahi mili!")
        return

    conn = sqlite3.connect(DB_PATH)

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
        """)

        tables = cursor.fetchall()

        if not tables:
            print("Database mein koi table nahi mili.")
            return

        print("\n========== DATABASE TABLES ==========")

        for (table_name,) in tables:
            print(f"\n{'=' * 60}")
            print(f"TABLE: {table_name}")
            print("=" * 60)

            cursor.execute(f'SELECT * FROM "{table_name}"')

            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()

            print("Columns:", columns)
            print("Total records:", len(rows))

            for row in rows:
                print(row)

        print("\nDatabase successfully read.")

    except sqlite3.Error as error:
        print(f"SQLite error: {error}")

    finally:
        conn.close()


if __name__ == "__main__":
    view_database()
