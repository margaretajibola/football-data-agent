import os
from datetime import date, datetime
from decimal import Decimal

import psycopg2
from dotenv import load_dotenv

load_dotenv()

MAX_ROWS = 100

def get_conn():
    # read-only role, never the main DATABASE_URL
    return psycopg2.connect(os.getenv("READONLY_DATABASE_URL"))


def clean(value):
    # make database values JSON friendly
    if isinstance(value, (date, datetime, Decimal)):
        return str(value)
    return value

def fetch(sql, params=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        columns = [d[0] for d in cur.description]
        rows = [[clean(v) for v in row] for row in cur.fetchall()]
    return columns, rows

def check_select(sql):
    # allow a single SELECT or WITH statement only
    sql = sql.strip().rstrip(";").strip()
    if ";" in sql:
        raise ValueError("Only one statement is allowed.")
    if not sql.lower().startswith(("select", "with")):
        raise ValueError("Only SELECT queries are allowed.")
    return sql


def run_select(sql):
    sql = check_select(sql)
    # wrap the query so the row limit is always enforced
    limited = f"SELECT * FROM ({sql}) AS q LIMIT {MAX_ROWS}"
    columns, rows = fetch(limited)
    return {"columns": columns, "rows": rows, "row_count": len(rows),
            "limited_to": MAX_ROWS}