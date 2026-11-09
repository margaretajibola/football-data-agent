# Pipeline structure

The pipeline pulls Premier League data from football-data.org, loads it into Neon Postgres, and rebuilds the analytics views the agent queries. It runs once a day.

## Flow

```
football-data.org API
        |
   extract.py      saves raw JSON to data/raw/ (timestamped)
        |
   transform.py    turns raw JSON into row tuples
        |
   load.py         upserts into the fd schema, then rebuilds analytics views
        |
Neon Postgres
  fd.*             raw tables (teams, matches, standings, scorers)
  analytics.*      views the agent reads
```

## Files

| Path | Purpose |
|---|---|
| `pipeline/config.py` | Shared settings |
| `pipeline/extract.py` | Calls the API and saves raw JSON. Waits 7s between calls (free tier allows 10 requests per minute). Fails the run if teams, matches or standings cannot be fetched. Scorers are optional. |
| `pipeline/transform.py` | Converts each raw file into rows. Uses `[]` for required fields and `.get` for optional ones. |
| `pipeline/load.py` | Runs `sql/schema.sql`, upserts all tables in one transaction (teams first for foreign keys), then runs `sql/views.sql`. |
| `pipeline/run.py` | Single entry point: extract, then load. Used by both schedulers. |
| `sql/schema.sql` | Tables in the `fd` schema |
| `sql/views.sql` | Views in the `analytics` schema |
| `sql/readonly_role.sql` | Record of the read-only role setup (password is a placeholder) |
| `.github/workflows/daily_pipeline.yml` | Scheduled GitHub Actions run |
| `dags/football_dag.py` | Airflow DAG for running the same pipeline locally. See the Airflow setup section below. |

## Design choices

- **Idempotent loads.** Every table uses `INSERT ... ON CONFLICT DO UPDATE`, so rerunning the pipeline never creates duplicates.
- **One transaction.** If any step in the load fails, nothing is committed.
- **Raw data kept.** Raw JSON is saved before transforming, so a transform bug can be fixed and replayed without calling the API again.
- **Snapshots.** Standings and scorers are stored per `snapshot_date`, which gives history over time.
- **Separate schemas.** `fd` holds the loaded data, `analytics` holds the views. The agent's read-only role can only see `analytics`.

## Scheduling

Both schedulers run `pipeline.run` once a day, scheduled for 06:30 UTC. GitHub Actions treats the schedule as a best effort, so a run can start a few hours late. This does not matter because every load is idempotent.

- **GitHub Actions** is the real daily run. It uses the repo secrets `FOOTBALL_DATA_API_KEY` and `DATABASE_URL`, and can also be started by hand from the Actions tab.
- **Airflow** is a local version of the same pipeline, with two tasks (extract, then load), `catchup=False`, and two retries five minutes apart.

## Run it by hand

```
python3 -m pipeline.run
```

## Set up Airflow locally

Use a separate virtual environment from the project one. Airflow's dependencies clash with the LangChain packages.

1. Create and activate a new venv outside the project folder:

```
python3.12 -m venv ~/airflow-venv
source ~/airflow-venv/bin/activate
```

2. Install Airflow. Use the install command and constraints file for the current version from the official Airflow docs (Installation, "Installation from PyPI"). The constraints file pins compatible package versions, so do not skip it.

3. Install the pipeline packages in the same venv:

```
pip install requests python-dotenv psycopg2-binary
```

4. Point Airflow at the repo's DAG folder. Quote the path if it has spaces:

```
export AIRFLOW__CORE__DAGS_FOLDER="/path/to/football_data_agent/dags"
export AIRFLOW__CORE__LOAD_EXAMPLES=False
```

5. Make sure `.env` in the project root has `FOOTBALL_DATA_API_KEY` and `DATABASE_URL`. The DAG imports `pipeline`, which loads it.

6. Start Airflow:

```
airflow standalone
```

7. Open `http://localhost:8080`. The login is printed in the terminal on first start.

8. Find `football_daily_pipeline`, unpause it, and trigger it with the play button. Both tasks (extract, load) should turn green.

### Troubleshooting

- **DAG not listed:** check the dags folder path and look for import errors at the top of the UI.
- **Import error on `pipeline`:** the DAG adds the project root to the path, so confirm the file is at `dags/football_dag.py` inside the repo.
- **Extract task slow:** this is normal, the script waits 7 seconds between API calls.
- **Stop Airflow:** press Ctrl+C in the terminal.

## Known limits

- Free tier gives the current season only, and only TOTAL standings (home and away tables are built in the views).
- Fixtures include future matches with null scores.
- Neon free tier can pause, so the first connection after a quiet period may be slow.
- GitHub pauses scheduled workflows after 60 days without commits in the repo. A new commit or a manual run restarts them.