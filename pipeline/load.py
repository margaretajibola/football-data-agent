import json
import os
from datetime import date
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

from pipeline.transform import matches_rows, scorers_rows, standings_rows, teams_rows

load_dotenv()

ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "data" / "raw"

# read the newest raw file saved for an endpoint
def latest_raw(name):
    files = sorted(RAW_DIR.glob(f"football_data_PL_{name}_*.json"))
    return json.loads(files[-1].read_text())

# insert new rows, update existing ones, so reruns never duplicate
def upsert(cur, table, columns, key, rows):
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in columns if c not in key)
    sql = (
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES %s "
        f"ON CONFLICT ({', '.join(key)}) DO UPDATE SET {updates}"
    )
    execute_values(cur, sql, rows)
    print(f"{table}: {len(rows)} rows")

def load_all():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    with conn, conn.cursor() as cur:
        cur.execute((ROOT / "sql" / "schema.sql").read_text())

        # teams first, because the other tables point to them
        upsert(cur, "fd.teams",
               ["team_id", "name", "short_name", "tla", "founded", "venue", "club_colors"],
               ["team_id"], teams_rows(latest_raw("teams")))

        upsert(cur, "fd.matches",
               ["match_id", "season_year", "matchday", "status", "utc_date",
                "home_team_id", "away_team_id", "home_goals", "away_goals",
                "half_time_home", "half_time_away", "winner", "last_updated"],
               ["match_id"], matches_rows(latest_raw("matches")))

        upsert(cur, "fd.standings",
               ["snapshot_date", "season_year", "table_type", "position", "team_id",
                "played", "won", "draw", "lost", "points", "goals_for",
                "goals_against", "goal_diff"],
               ["snapshot_date", "table_type", "team_id"],
               standings_rows(latest_raw("standings"), date.today()))

        upsert(cur, "fd.scorers",
               ["snapshot_date", "season_year", "player_id", "player_name",
                "nationality", "position", "team_id", "played_matches",
                "goals", "assists", "penalties"],
               ["snapshot_date", "player_id"],
               scorers_rows(latest_raw("scorers"), date.today()))

        # rebuild the views the agent will query
        cur.execute((ROOT / "sql" / "views.sql").read_text())
        print("analytics views created")
    conn.close()


if __name__ == "__main__":
    load_all()