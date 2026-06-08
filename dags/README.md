# Airflow DAGs — Placeholder

DAGs are implemented in Bloc 3.

Planned DAGs:
- `ingest_shopify.py` — pull orders/customers from Shopify API → Bronze (MinIO)
- `ingest_marketing.py` — pull marketing events → Bronze
- `dbt_run.py` — trigger dbt Bronze→Silver→Gold transformations
- `data_quality.py` — run Great Expectations checkpoints; alert on failure
