# Airflow image with the pipeline's Python dependencies added.
# The constraints file pins versions that are tested to work with this Airflow release.
FROM apache/airflow:slim-2.10.5-python3.11

RUN pip install --no-cache-dir \
    "apache-airflow==2.10.5" pandas openpyxl pymysql python-dotenv \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.11.txt"
