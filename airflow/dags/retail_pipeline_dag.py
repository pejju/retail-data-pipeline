"""Airflow DAG that orchestrates the retail ETL pipeline.

    create_schema -> extract_transform -> load_warehouse -> data_quality_checks -> refresh_rfm_view

Each stage is its own task, so it can be monitored and retried separately. Tasks pass a file path
to each other (not a DataFrame): XComs are meant for small values, and the cleaned CSV on disk is
the hand-off between stages. If data_quality_checks fails, refresh_rfm_view never runs, so bad data
never reaches the Power BI dashboard.
"""
from datetime import datetime, timedelta

from airflow.decorators import dag, task

default_args = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def _engine():
    from sqlalchemy import create_engine
    from retail_pipeline import config
    return create_engine(config.database_url())


@dag(
    dag_id="retail_pipeline",
    description="Online Retail II: extract, clean, load star schema, quality checks, RFM view",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["retail", "etl"],
)
def retail_pipeline():

    @task
    def create_schema() -> None:
        from retail_pipeline import load
        load.create_schema(_engine())

    @task
    def extract_transform() -> str:
        from retail_pipeline import config, extract, transform
        clean = transform.transform(extract.extract_raw())
        transform.save_processed(clean)
        return str(config.CLEAN_FILE)

    @task
    def load_warehouse(clean_path: str) -> str:
        from retail_pipeline import load, transform
        load.load_all(transform.read_processed(clean_path), _engine())
        return clean_path

    @task
    def data_quality_checks(clean_path: str) -> None:
        from retail_pipeline import quality, transform
        quality.run_checks(transform.read_processed(clean_path), _engine())

    @task
    def refresh_rfm_view() -> None:
        from retail_pipeline import load
        load.refresh_rfm_view(_engine())

    schema = create_schema()
    clean_path = extract_transform()
    schema >> clean_path
    loaded = load_warehouse(clean_path)
    data_quality_checks(loaded) >> refresh_rfm_view()


retail_pipeline()
