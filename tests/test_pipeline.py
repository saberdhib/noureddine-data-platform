"""
Pipeline smoke tests — Bloc 3.

Run after a full history + dbt build cycle:
  pytest tests/test_pipeline.py -v

Requires:
  - DATABASE_URL env var pointing to a running postgres
  - The simulator history mode to have run at least once
  - `dbt build` to have completed
"""
import os
from datetime import date

import pytest
import sqlalchemy as sa

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://noureddine_user:change_me_postgres@localhost:5432/noureddine",
)


@pytest.fixture(scope="session")
def engine():
    e = sa.create_engine(DB_URL, future=True)
    yield e
    e.dispose()


def scalar(engine, sql, params=None):
    with engine.connect() as conn:
        return conn.execute(sa.text(sql), params or {}).scalar()


# ---------------------------------------------------------------------------
# OLTP checks
# ---------------------------------------------------------------------------

def test_oltp_customers_populated(engine):
    count = scalar(engine, "SELECT COUNT(*) FROM oltp.customers")
    assert count >= 1000, f"Expected ≥1000 customers, got {count}"


def test_oltp_orders_populated(engine):
    count = scalar(engine, "SELECT COUNT(*) FROM oltp.orders")
    assert count >= 5000, f"Expected ≥5000 orders, got {count}"


def test_calendar_events_exist(engine):
    """Fixed Islamic calendar windows must be seeded."""
    count = scalar(engine, "SELECT COUNT(*) FROM oltp.calendar_events")
    assert count >= 12, f"Expected ≥12 calendar events, got {count}"

    for name in ("Ramadan 2024", "Eid al-Fitr 2025", "Eid al-Adha 2026"):
        found = scalar(
            engine,
            "SELECT COUNT(*) FROM oltp.calendar_events WHERE event_name = :n",
            {"n": name},
        )
        assert found == 1, f"calendar_events missing: {name}"


# ---------------------------------------------------------------------------
# Silver checks
# ---------------------------------------------------------------------------

def test_silver_stg_orders_populated(engine):
    count = scalar(engine, "SELECT COUNT(*) FROM silver.stg_orders")
    assert count >= 5000, f"silver.stg_orders has only {count} rows"


def test_silver_stg_customers_populated(engine):
    count = scalar(engine, "SELECT COUNT(*) FROM silver.stg_customers")
    assert count >= 1000, f"silver.stg_customers has only {count} rows"


# ---------------------------------------------------------------------------
# Gold checks
# ---------------------------------------------------------------------------

def test_gold_fact_sales_populated(engine):
    count = scalar(engine, "SELECT COUNT(*) FROM gold.fact_sales")
    assert count >= 5000, f"gold.fact_sales is nearly empty ({count} rows)"


def test_gold_dim_product_populated(engine):
    count = scalar(engine, "SELECT COUNT(*) FROM gold.dim_product")
    assert count >= 100, f"gold.dim_product has only {count} rows"


def test_gold_dim_date_populated(engine):
    count = scalar(engine, "SELECT COUNT(*) FROM gold.dim_date")
    assert count >= 365, f"gold.dim_date has only {count} rows"


def test_no_negative_revenue(engine):
    bad = scalar(engine, "SELECT COUNT(*) FROM gold.fact_sales WHERE revenue < 0")
    assert bad == 0, f"Found {bad} negative-revenue rows in fact_sales"


def test_no_orphan_fact_sales(engine):
    orphans = scalar(engine, "SELECT COUNT(*) FROM gold.fact_sales WHERE customer_key IS NULL")
    assert orphans == 0, f"Found {orphans} orphan rows (null customer_key) in fact_sales"


# ---------------------------------------------------------------------------
# Seasonality visibility
# ---------------------------------------------------------------------------

def test_seasonality_eid_vs_baseline(engine):
    """Pre-Eid al-Fitr 2025 window (Mar 17–30) must have materially higher order volume
    than an equal-length baseline window (e.g. Feb 1–14 2025)."""
    eid_count = scalar(
        engine,
        "SELECT COUNT(*) FROM oltp.orders "
        "WHERE order_date::date BETWEEN '2025-03-17' AND '2025-03-30'",
    )
    baseline_count = scalar(
        engine,
        "SELECT COUNT(*) FROM oltp.orders "
        "WHERE order_date::date BETWEEN '2025-02-01' AND '2025-02-14'",
    )
    # Eid window multiplier is ~4x; allow for noise/growth but expect at least 2x
    assert eid_count >= 2 * max(baseline_count, 1), (
        f"Seasonality not visible: Eid={eid_count}, baseline={baseline_count}"
    )
