import sys
from datetime import datetime, timedelta
from pathlib import Path

# works on Airflow 3 and Airflow 2
try:
    from airflow.sdk import dag, task
except ImportError:
    from airflow.decorators import dag, task

# make the project's pipeline package importable inside Airflow
sys.path.append(str(Path(__file__).parent.parent))


@dag(
    dag_id="football_daily_pipeline",
    schedule="30 6 * * *",
    start_date=datetime(2026, 11, 1),
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["football"],
)
def football_daily_pipeline():
    @task
    def extract():
        from pipeline.extract import extract_all
        extract_all()

    @task
    def load():
        from pipeline.load import load_all
        load_all()

    extract() >> load()


football_daily_pipeline()