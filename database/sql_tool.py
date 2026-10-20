
import json
import sqlite3
from pathlib import Path

from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool


DB_PATH = Path(__file__).resolve().parent / "company.db"


class SQLQueryInput(BaseModel):
    sql_query: str = Field(
        description=(
            "A single read-only SQL SELECT query. "
            "Available tables: departments(department_id, "
            "department_name, location), "
            "employees(employee_id, name, email, salary, "
            "department_id), "
            "projects(project_id, project_name, budget, "
            "employee_id). Use JOINs for related information."
        )
    )


def execute_sql_query(sql_query: str) -> str:
    """Execute a single read-only SELECT query."""

    query = sql_query.strip()

    if not query:
        return "Error: SQL query is empty."

    # Permit one optional trailing semicolon only.
    query = query.removesuffix(";").strip()

    # Reject multiple statements and non-read-only SQL.
    if ";" in query:
        return "Error: Only one SQL statement is allowed."

    first_keyword = query.split(maxsplit=1)[0].upper()

    if first_keyword not in {"SELECT", "WITH"}:
        return "Error: Only SELECT queries are allowed."

    if not DB_PATH.exists():
        return (
            "Error: Database not found. "
            "Run python -m database.db_setup first."
        )

    try:
        # mode=ro prevents database writes.
        uri = DB_PATH.as_uri() + "?mode=ro"

        with sqlite3.connect(uri, uri=True, timeout=5) as conn:
            conn.row_factory = sqlite3.Row

            cursor = conn.execute(query)
            rows = [dict(row) for row in cursor.fetchall()]

        return json.dumps(
            {
                "success": True,
                "row_count": len(rows),
                "results": rows,
            },
            ensure_ascii=False,
            default=str,
        )

    except sqlite3.Error as exc:
        return json.dumps({
            "success": False,
            "error": str(exc),
        })


sql_database_tool = StructuredTool.from_function(
    func=execute_sql_query,
    name="query_sql_database",
    description=(
        "Use this tool to answer questions about company departments, "
        "employees, salaries, project budgets, project assignments, "
        "counts, totals, averages, and comparisons. "
        "Generate a valid SQLite SELECT query using the provided schema. "
        "Use JOINs when information spans multiple tables. "
        "Base the answer on the returned rows; never invent database data."
    ),
    args_schema=SQLQueryInput,
)
