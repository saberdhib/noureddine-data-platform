"""Read-only Postgres access for the Streamlit business app (Bloc 4).

Streamlit reads ONLY gold tables + inventory + calendar_events (governance:
business consumption, no PII beyond aggregate dims). It must NEVER load the model
directly — forecasts come from the FastAPI service (see ``api_client``).
"""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text


def _database_url() -> str:
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    user = os.getenv("POSTGRES_USER", "noureddine_user")
    pwd = os.getenv("POSTGRES_PASSWORD", "change_me_postgres")
    host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "noureddine")
    return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"


@st.cache_resource(show_spinner=False)
def get_engine():
    return create_engine(_database_url(), pool_pre_ping=True)


@st.cache_data(ttl=300, show_spinner=False)
def run_query(sql: str, params: dict | None = None) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


# --- gold / inventory / calendar helpers ------------------------------------
def kpis(start: str, end: str) -> pd.DataFrame:
    return run_query("""
        SELECT
            COALESCE(SUM(f.revenue),0)            AS revenue,
            COUNT(DISTINCT f.order_id)            AS orders,
            COALESCE(SUM(f.quantity),0)           AS units,
            CASE WHEN COUNT(DISTINCT f.order_id)=0 THEN 0
                 ELSE SUM(f.revenue)/COUNT(DISTINCT f.order_id) END AS aov
        FROM gold.fact_sales f
        JOIN gold.dim_date d ON d.date_key=f.date_key
        WHERE d.date BETWEEN :s AND :e
    """, {"s": start, "e": end})


def revenue_by_day(start: str, end: str) -> pd.DataFrame:
    return run_query("""
        SELECT d.date AS date, SUM(f.revenue) AS revenue, SUM(f.quantity) AS units
        FROM gold.fact_sales f JOIN gold.dim_date d ON d.date_key=f.date_key
        WHERE d.date BETWEEN :s AND :e GROUP BY d.date ORDER BY d.date
    """, {"s": start, "e": end})


def top_categories(start: str, end: str) -> pd.DataFrame:
    return run_query("""
        SELECT p.category AS category, SUM(f.revenue) AS revenue, SUM(f.quantity) AS units
        FROM gold.fact_sales f
        JOIN gold.dim_date d ON d.date_key=f.date_key
        JOIN gold.dim_product p ON p.product_key=f.product_key
        WHERE d.date BETWEEN :s AND :e
        GROUP BY p.category ORDER BY revenue DESC
    """, {"s": start, "e": end})


def top_channels(start: str, end: str) -> pd.DataFrame:
    return run_query("""
        SELECT c.channel_name AS channel, SUM(f.revenue) AS revenue
        FROM gold.fact_sales f
        JOIN gold.dim_date d ON d.date_key=f.date_key
        JOIN gold.dim_channel c ON c.channel_key=f.channel_key
        WHERE d.date BETWEEN :s AND :e
        GROUP BY c.channel_name ORDER BY revenue DESC
    """, {"s": start, "e": end})


def category_history(category: str, days: int = 90) -> pd.DataFrame:
    return run_query("""
        SELECT d.date AS date, SUM(f.quantity) AS units
        FROM gold.fact_sales f
        JOIN gold.dim_date d ON d.date_key=f.date_key
        JOIN gold.dim_product p ON p.product_key=f.product_key
        WHERE p.category=:cat
        GROUP BY d.date ORDER BY d.date DESC LIMIT :days
    """, {"cat": category, "days": days})


def categories() -> list[str]:
    df = run_query("SELECT DISTINCT category FROM gold.dim_product WHERE category IS NOT NULL ORDER BY category")
    return df["category"].tolist()


def inventory_by_category() -> pd.DataFrame:
    return run_query("""
        SELECT p.category AS category, SUM(i.stock_quantity) AS stock
        FROM oltp.inventory i
        JOIN oltp.products op ON op.product_id=i.product_id
        JOIN oltp.categories c ON c.category_id=op.category_id
        JOIN gold.dim_product p ON p.product_id=i.product_id
        GROUP BY p.category ORDER BY p.category
    """)


def calendar_events() -> pd.DataFrame:
    return run_query("SELECT event_name, event_type, start_date, end_date FROM oltp.calendar_events")
