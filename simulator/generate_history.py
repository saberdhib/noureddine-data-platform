"""
generate_history.py — NOUREDDINE data simulator (history / backfill mode).

Generates ~3 years of realistic e-commerce activity (2023-07-01 -> today):
  - ~15k customers, ~300 products across 7 categories, ~20k orders
  - order dates distributed by the fixed Islamic-calendar seasonality model
  - writes to schema `oltp` via SQLAlchemy AND dumps raw JSON to MinIO bronze

--reset truncates business tables (keeps categories + calendar_events) first.

NEVER computes Hijri dates — all seasonality comes from simulator/seasonality.py.
"""
import argparse
import os
import random
import uuid
from datetime import date, timedelta, datetime

import numpy as np
from faker import Faker
from sqlalchemy import text

from common import (
    get_engine, get_s3, ensure_bucket, put_bronze,
    CATEGORIES, CHANNELS, CATEGORY_PRICE_BAND, BUSINESS_TABLES,
)
from seasonality import demand_multiplier, CALENDAR_EVENTS, get_calendar_event_name

fake = Faker(["fr_FR", "en_GB"])

N_CUSTOMERS = int(os.environ.get("SIM_N_CUSTOMERS", 15000))
N_PRODUCTS = int(os.environ.get("SIM_N_PRODUCTS", 300))
N_ORDERS = int(os.environ.get("SIM_N_ORDERS", 20000))
START_DATE = date(2023, 7, 1)

SEASON_TAGS = ["ramadan", "eid", "nikah", "year-round", "year-round"]


# ---------------------------------------------------------------------------
# Reset / reference data
# ---------------------------------------------------------------------------
def reset_business_tables(conn):
    print("[reset] truncating business tables (keeping categories + calendar_events)")
    conn.execute(text(
        "TRUNCATE TABLE oltp." + ", oltp.".join(BUSINESS_TABLES) + " RESTART IDENTITY CASCADE"
    ))


def ensure_categories(conn):
    """Reference categories are seeded by Bloc 2; ensure all 7 exist and return id map."""
    for name, _tag in CATEGORIES:
        conn.execute(text(
            "INSERT INTO oltp.categories (category_name) VALUES (:n) "
            "ON CONFLICT (category_name) DO NOTHING"
        ), {"n": name})
    rows = conn.execute(text("SELECT category_id, category_name FROM oltp.categories")).fetchall()
    return {r.category_name: r.category_id for r in rows}


def ensure_calendar_events(conn):
    """Upsert fixed Islamic-calendar windows into oltp.calendar_events.
    Dates are NEVER computed — they are taken from CALENDAR_EVENTS in seasonality.py (CLAUDE.md §9).
    """
    all_events = list(CALENDAR_EVENTS)
    # Add Nikah season rows for each year in range
    for year in range(2023, 2027):
        all_events.append({
            "name": f"Nikah Season {year}",
            "type": "nikah",
            "start": date(year, 6, 1),
            "end": date(year, 8, 31),
        })
        # Black Friday — last Friday of November
        bf = date(year, 11, 30)
        while bf.weekday() != 4:
            bf -= timedelta(days=1)
        all_events.append({
            "name": f"Black Friday {year}",
            "type": "black_friday",
            "start": bf,
            "end": bf,
        })

    for ev in all_events:
        conn.execute(text(
            "INSERT INTO oltp.calendar_events (event_name, event_type, start_date, end_date) "
            "SELECT :name, :type, :start, :end "
            "WHERE NOT EXISTS ("
            "  SELECT 1 FROM oltp.calendar_events WHERE event_name = :name"
            ")"
        ), {"name": ev["name"], "type": ev["type"], "start": ev["start"], "end": ev["end"]})
    count = conn.execute(text("SELECT COUNT(*) FROM oltp.calendar_events")).scalar()
    print(f"[calendar] {count} calendar events in oltp.calendar_events")


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------
def gen_customers(n):
    custs = []
    for _ in range(n):
        cid = uuid.uuid4()
        created = fake.date_time_between(start_date=START_DATE, end_date="now")
        custs.append({
            "customer_id": cid,
            "email": f"{uuid.uuid4().hex[:10]}@example.test",
            "first_name": fake.first_name_male(),
            "last_name": fake.last_name(),
            "country": random.choice(["France", "France", "France", "United Kingdom", "Germany", "Belgium"]),
            "city": fake.city(),
            "consent_marketing": random.random() < 0.6,
            "acquisition_source": random.choice(CHANNELS),
            "created_at": created,
            "updated_at": created,
        })
    return custs


def gen_products(n, cat_ids):
    prods = []
    for i in range(n):
        cat_name, _ = random.choice(CATEGORIES)
        lo, hi = CATEGORY_PRICE_BAND[cat_name]
        price = round(random.uniform(lo, hi), 2)
        prods.append({
            "product_id": uuid.uuid4(),
            "sku": f"NRD-{cat_name[:3].upper()}-{i:05d}",
            "product_name": f"{cat_name} {fake.color_name()} {fake.word().capitalize()}",
            "category_id": cat_ids[cat_name],
            "category_name": cat_name,
            "price_eur": price,
            "cost_eur": round(price * random.uniform(0.45, 0.65), 2),
            "seasonality_tag": random.choice(SEASON_TAGS),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        })
    return prods


def generate_order_dates(n_orders, start=START_DATE, end=None):
    end = end or date.today()
    all_dates = []
    d = start
    while d <= end:
        all_dates.append(d)
        d += timedelta(days=1)
    weights = np.array([
        float(np.mean([demand_multiplier(dd, cat) for cat, _ in CATEGORIES]))
        for dd in all_dates
    ])
    weights /= weights.sum()
    idx = np.random.choice(len(all_dates), size=n_orders, p=weights)
    return [all_dates[i] for i in idx]


def pick_product_for_date(products, d):
    """Weight product choice by category demand on date d."""
    weights = np.array([demand_multiplier(d, p["category_name"]) for p in products])
    weights /= weights.sum()
    return products[int(np.random.choice(len(products), p=weights))]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(reset):
    engine = get_engine()
    s3 = get_s3()
    ensure_bucket(s3)

    with engine.begin() as conn:
        if reset:
            reset_business_tables(conn)
        cat_ids = ensure_categories(conn)
        ensure_calendar_events(conn)

        print(f"[gen] {N_CUSTOMERS} customers, {N_PRODUCTS} products, {N_ORDERS} orders")
        customers = gen_customers(N_CUSTOMERS)
        products = gen_products(N_PRODUCTS, cat_ids)

        conn.execute(text(
            "INSERT INTO oltp.customers "
            "(customer_id,email,first_name,last_name,country,city,consent_marketing,"
            "acquisition_source,created_at,updated_at) VALUES "
            "(:customer_id,:email,:first_name,:last_name,:country,:city,:consent_marketing,"
            ":acquisition_source,:created_at,:updated_at)"
        ), customers)

        conn.execute(text(
            "INSERT INTO oltp.products "
            "(product_id,sku,product_name,category_id,price_eur,cost_eur,seasonality_tag,"
            "created_at,updated_at) VALUES "
            "(:product_id,:sku,:product_name,:category_id,:price_eur,:cost_eur,:seasonality_tag,"
            ":created_at,:updated_at)"
        ), [{k: p[k] for k in (
            "product_id", "sku", "product_name", "category_id", "price_eur",
            "cost_eur", "seasonality_tag", "created_at", "updated_at")} for p in products])

        # Inventory: one row per product
        conn.execute(text(
            "INSERT INTO oltp.inventory (product_id,stock_quantity,reorder_threshold) "
            "VALUES (:pid,:stock,:thr)"
        ), [{"pid": p["product_id"], "stock": random.randint(0, 500),
             "thr": random.randint(10, 50)} for p in products])

        order_dates = generate_order_dates(N_ORDERS)
        carriers = ["Colissimo", "Chronopost", "DHL", "DPD", "Mondial Relay"]
        statuses_pay = ["paid", "paid", "paid", "pending", "refunded"]
        statuses_ord = ["delivered", "shipped", "processing", "cancelled"]

        orders, items, shipments, mkt, rag = [], [], [], [], []
        for od in order_dates:
            order_id = uuid.uuid4()
            cust = random.choice(customers)
            n_lines = random.randint(1, 4)
            line_rows = []
            total = 0.0
            for _ in range(n_lines):
                prod = pick_product_for_date(products, od)
                qty = random.randint(1, 3)
                unit = float(prod["price_eur"])
                line_total = round(unit * qty, 2)
                total += line_total
                line_rows.append({
                    "order_item_id": uuid.uuid4(), "order_id": order_id,
                    "product_id": prod["product_id"], "quantity": qty,
                    "unit_price": unit, "line_total": line_total,
                })
            discount = round(total * random.choice([0, 0, 0, 0.1, 0.15]), 2)
            shipping = round(random.choice([0, 4.95, 6.95, 9.95]), 2)
            order_ts = datetime.combine(od, datetime.min.time()) + timedelta(
                hours=random.randint(8, 22), minutes=random.randint(0, 59))
            channel = cust["acquisition_source"]
            orders.append({
                "order_id": order_id, "customer_id": cust["customer_id"],
                "order_date": order_ts, "total_amount": round(total, 2),
                "discount_amount": discount, "shipping_cost": shipping,
                "payment_status": random.choice(statuses_pay),
                "order_status": random.choice(statuses_ord),
                "acquisition_channel": channel, "created_at": order_ts,
            })
            items.extend(line_rows)
            ship_date = od + timedelta(days=random.randint(0, 2))
            shipments.append({
                "shipment_id": uuid.uuid4(), "order_id": order_id,
                "carrier": random.choice(carriers),
                "tracking_number": fake.bothify("??########"),
                "shipping_date": ship_date,
                "delivery_date": ship_date + timedelta(days=random.randint(1, 5)),
                "shipment_status": random.choice(["delivered", "in_transit", "pending"]),
            })
            if random.random() < 0.7:
                mkt.append({
                    "event_id": uuid.uuid4(), "customer_id": cust["customer_id"],
                    "source": channel, "campaign_name": fake.catch_phrase(),
                    "event_type": random.choice(["click", "impression", "conversion"]),
                    "event_timestamp": order_ts - timedelta(hours=random.randint(1, 48)),
                })
            if random.random() < 0.4:
                rag.append({
                    "conversation_id": uuid.uuid4(), "customer_id": cust["customer_id"],
                    "question": random.choice([
                        "Quelle taille de qamis pour moi ?",
                        "What beard oil do you recommend?",
                        "Avez-vous un coffret cadeau pour l'Aid ?",
                        "Which suit fits a slim build?",
                    ]),
                    "intent": random.choice(["sizing", "recommendation", "gift", "styling"]),
                    "conversation_timestamp": order_ts - timedelta(hours=random.randint(1, 24)),
                })

        _bulk(conn, "orders", orders,
              "order_id,customer_id,order_date,total_amount,discount_amount,shipping_cost,"
              "payment_status,order_status,acquisition_channel,created_at")
        _bulk(conn, "order_items", items,
              "order_item_id,order_id,product_id,quantity,unit_price,line_total")
        _bulk(conn, "shipments", shipments,
              "shipment_id,order_id,carrier,tracking_number,shipping_date,delivery_date,shipment_status")
        if mkt:
            _bulk(conn, "marketing_events", mkt,
                  "event_id,customer_id,source,campaign_name,event_type,event_timestamp")
        if rag:
            _bulk(conn, "rag_conversations", rag,
                  "conversation_id,customer_id,question,intent,conversation_timestamp")

    # Bronze dump (best-effort): one daily batch summary per order date
    print("[bronze] dumping raw order batches to MinIO bronze bucket")
    by_day = {}
    for o in orders:
        by_day.setdefault(o["order_date"].date().isoformat(), []).append(str(o["order_id"]))
    for day, ids in by_day.items():
        put_bronze(s3, f"orders/history/{day}/batch.json",
                   {"date": day, "event": get_calendar_event_name(date.fromisoformat(day)),
                    "order_ids": ids, "count": len(ids)})

    print(f"[done] inserted {len(orders)} orders, {len(items)} order_items")


def _bulk(conn, table, rows, cols):
    placeholders = ",".join(f":{c.strip()}" for c in cols.split(","))
    conn.execute(text(f"INSERT INTO oltp.{table} ({cols}) VALUES ({placeholders})"), rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true",
                    help="truncate business tables (keep categories + calendar_events) before generating")
    args = ap.parse_args()
    main(reset=args.reset)
