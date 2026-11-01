import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv("READONLY_DATABASE_URL"))
cur = conn.cursor()


def try_sql(sql):
    try:
        cur.execute(sql)
        print("OK  ", sql, "->", cur.fetchall()[:2] if cur.description else "")
    except Exception as e:
        print("FAIL", sql, "->", str(e).splitlines()[0])
        conn.rollback()


# the first one should work, the rest should all fail
try_sql("SELECT team, points FROM league_table WHERE venue = 'ALL' ORDER BY position LIMIT 3")
try_sql("SELECT * FROM fd.matches LIMIT 1")
try_sql("DELETE FROM fd.teams")
try_sql("DROP VIEW analytics.teams")
try_sql("SELECT pg_sleep(15)")