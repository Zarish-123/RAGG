
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "company.db"


def create_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        conn.executescript("""
        CREATE TABLE IF NOT EXISTS departments (
            department_id INTEGER PRIMARY KEY,
            department_name TEXT NOT NULL UNIQUE,
            location TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS employees (
            employee_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            salary REAL NOT NULL CHECK (salary >= 0),
            department_id INTEGER NOT NULL,
            FOREIGN KEY (department_id)
                REFERENCES departments(department_id)
        );

        CREATE TABLE IF NOT EXISTS projects (
            project_id INTEGER PRIMARY KEY,
            project_name TEXT NOT NULL,
            budget REAL NOT NULL CHECK (budget >= 0),
            employee_id INTEGER NOT NULL,
            FOREIGN KEY (employee_id)
                REFERENCES employees(employee_id)
        );
        """)

        # Insert sample data only if the tables are empty.
        if conn.execute(
            "SELECT COUNT(*) FROM departments"
        ).fetchone()[0] == 0:
            conn.executemany(
                """
                INSERT INTO departments
                (department_id, department_name, location)
                VALUES (?, ?, ?)
                """,
                [
                    (1, "AI", "Islamabad"),
                    (2, "Data Science", "Lahore"),
                    (3, "Software Engineering", "Karachi"),
                    (4, "Cybersecurity", "Islamabad"),
                    (5, "Cloud Computing", "Lahore"),
                ],
            )

        if conn.execute(
            "SELECT COUNT(*) FROM employees"
        ).fetchone()[0] == 0:
            conn.executemany(
                """
                INSERT INTO employees
                (employee_id, name, email, salary, department_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (101, "Ali", "ali@example.com", 120000, 1),
                    (102, "Sara", "sara@example.com", 135000, 2),
                    (103, "Ahmed", "ahmed@example.com", 110000, 1),
                    (104, "Ayesha", "ayesha@example.com", 145000, 3),
                    (105, "Usman", "usman@example.com", 100000, 4),
                    (106, "Hina", "hina@example.com", 125000, 2),
                    (107, "Bilal", "bilal@example.com", 115000, 3),
                    (108, "Zoya", "zoya@example.com", 150000, 5),
                    (109, "Hamza", "hamza@example.com", 105000, 4),
                    (110, "Mariam", "mariam@example.com", 140000, 5),
                ],
            )

        if conn.execute(
            "SELECT COUNT(*) FROM projects"
        ).fetchone()[0] == 0:
            conn.executemany(
                """
                INSERT INTO projects
                (project_id, project_name, budget, employee_id)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (201, "RAG Assistant", 500000, 101),
                    (202, "Sales Analytics", 350000, 102),
                    (203, "Image Classifier", 450000, 103),
                    (204, "Cloud Migration", 600000, 108),
                    (205, "Security Dashboard", 300000, 105),
                ],
            )

        conn.commit()

        # Verify total records.
        for table in ("departments", "employees", "projects"):
            count = conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
            print(f"{table}: {count} rows")

        total = conn.execute("""
            SELECT
                (SELECT COUNT(*) FROM departments) +
                (SELECT COUNT(*) FROM employees) +
                (SELECT COUNT(*) FROM projects)
        """).fetchone()[0]

        print(f"Total rows: {total}")
        print(f"Database path: {DB_PATH}")


if __name__ == "__main__":
    create_database()
