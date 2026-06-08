# dbt — NOUREDDINE Data Platform

## Status: Skeleton (Bloc 2)

Models are implemented in **Bloc 3**. This folder contains structure only.

## Project layout

```
dbt/noureddine/
├── dbt_project.yml          # project config: schemas, materialisations
├── profiles.yml.example     # copy to ~/.dbt/profiles.yml and fill in creds
└── models/
    ├── bronze/              # Bronze models: raw views over ingested data
    ├── silver/              # Silver models: cleaning, typing, dedup
    └── gold/                # Gold models: star schema population, metrics
```

## Planned models (Bloc 3)

| Layer  | Model                      | Description |
|--------|----------------------------|-------------|
| Bronze | `stg_shopify_orders.sql`   | Raw view over MinIO-ingested Shopify export |
| Bronze | `stg_marketing_events.sql` | Raw view over marketing event CSVs |
| Silver | `customers_clean.sql`      | Deduplicated, typed customer records |
| Silver | `orders_clean.sql`         | Validated orders with FK integrity checks |
| Gold   | `fact_sales.sql`           | Incremental fact_sales population |
| Gold   | `dim_customer.sql`         | SCD Type 1 dim_customer refresh |

## Quick start (Bloc 3+)

```bash
cp dbt/noureddine/profiles.yml.example ~/.dbt/profiles.yml
# Edit ~/.dbt/profiles.yml with your credentials
cd dbt/noureddine
dbt debug   # test connection
dbt run     # run all models
dbt test    # run data quality tests
```
