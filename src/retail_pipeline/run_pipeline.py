"""Run the whole pipeline end to end:

    create schema -> extract -> transform -> load -> data quality checks -> refresh RFM view

Usage (from the project root):
    python -m retail_pipeline.run_pipeline          (with PYTHONPATH=src)
or inside Docker:
    docker compose run --rm pipeline
"""
import logging
import time

from sqlalchemy import create_engine, text

from . import config, extract, load, quality, transform

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
log = logging.getLogger("pipeline")


def log_rfm_summary(engine) -> None:
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT Segment, COUNT(*) AS customers, ROUND(AVG(Monetary), 2) AS avg_spend
            FROM vw_customer_rfm GROUP BY Segment ORDER BY customers DESC""")).fetchall()
    for segment, customers, avg_spend in rows:
        log.info("RFM segment %-15s customers=%5d  avg_spend=%10.2f", segment, customers, avg_spend)


def main() -> None:
    started = time.time()
    engine = create_engine(config.database_url())

    log.info("Step 1/6 create schema (if missing)")
    load.create_schema(engine)

    log.info("Step 2/6 extract %s", config.RAW_FILE)
    raw = extract.extract_raw()
    log.info("Extracted %d rows", len(raw))

    log.info("Step 3/6 transform")
    clean = transform.transform(raw)
    transform.save_processed(clean)
    log.info("Cleaned: %d rows (%d duplicates removed), %d valid sales",
             len(clean), len(raw) - len(clean), int(clean["IsValidSale"].sum()))

    log.info("Step 4/6 load (full refresh)")
    load.load_all(clean, engine)

    log.info("Step 5/6 data quality checks")
    quality.run_checks(clean, engine)

    log.info("Step 6/6 refresh RFM view")
    load.refresh_rfm_view(engine)
    log_rfm_summary(engine)

    log.info("Pipeline finished in %.0f seconds", time.time() - started)


if __name__ == "__main__":
    main()
