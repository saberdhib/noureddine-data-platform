"""
drip.py — NOUREDDINE data simulator (live micro-batch mode).

Every DRIP_INTERVAL_SECONDS (default 10) inserts 1-5 new orders dated today,
weighted by today's seasonality, into oltp AND dumps raw JSON to MinIO bronze.

Mirrors the real back-office flow: an order hits OLTP, then Airflow's
micro-batch DAG (every 10 min) promotes it through silver/gold.
"""
import os
import random
import time
import uuid
from datetime import date, datetime

import numpy as np
from sqlalchemy import text

from common import get_engine, get_s3, ensure_bucket, put_bronze, CATEGORIES
from seasonality import demand_multiplier, get_calendar_event_name

INTERVAL = int(os.environ.get("DRIP_INTERVAL_SECONDS", 10))


def _load_refs(conn):
    customers = [r[0] for r in conn.execute(text("SELECT customer_id FROM oltp.customers")).fetchall()]
    products = conn.execute(text(
        "SELECT p.product_id, p.price_eur, c.category_name "
        "FROM oltp.products p JOIN oltp.categories c ON p.category_id = c.category_id"
    )).fetchall()
    return customers, products


def _pick_product(products, today):
    weights = np.array([demand_multiplier(today, p.category_name) for p in products])
    weights /= weights.sum()
    return products[int(np.random.choice(len(products), p=weights))]


def insert_batch(engine, s3, customers, products):
    today = date.today()
    n = random.randint(1, 5)
    new_ids = []
    with engine.begin() as conn:
        for _ in range(n):
            order_id = uuid.uuid4()
            cust = random.choice(customers)
            now = datetime.now()
            n_lines = random.randint(1, 3)
            total = 0.0
            lines = []
            for _ in range(n_lines):
                prod = _pick_product(products, today)
                qty = random.randint(1, 3)
                unit = float(prod.price_eur)
                lt = round(unit * qty, 2)
                total += lt
                lines.append((uuid.uuid4(), order_id, prod.product_id, qty, unit, lt))
            shipping = round(random.choice([0, 4.95, 6.95]), 2)
            conn.execute(text(
                "INSERT INTO oltp.orders (order_id,customer_id,order_date,total_amount,"
                "discount_amount,shipping_cost,payment_status,order_status,acquisition_channel,created_at) "
                "VALUES (:oid,:cid,:od,:tot,0,:ship,'paid','processing','direct',:od)"
            ), {"oid": order_id, "cid": cust, "od": now, "tot": round(total, 2), "ship": shipping})
            for li in lines:
                conn.execute(text(
                    "INSERT INTO oltp.order_items (order_item_id,order_id,product_id,quantity,"
                    "unit_price,line_total) VALUES (:oiid,:oid,:pid,:q,:u,:lt)"
                ), {"oiid": li[0], "oid": li[1], "pid": li[2], "q": li[3], "u": li[4], "lt": li[5]})
            new_ids.append(str(order_id))

    put_bronze(s3, f"orders/drip/{today.isoformat()}/{datetime.now().strftime('%H%M%S')}.json",
               {"ts": datetime.now().isoformat(), "event": get_calendar_event_name(today),
                "order_ids": new_ids, "count": len(new_ids)})
    print(f"[drip] {datetime.now().isoformat()} inserted {len(new_ids)} orders "
          f"(event={get_calendar_event_name(today)})")


def main():
    engine = get_engine()
    s3 = get_s3()
    ensure_bucket(s3)
    with engine.connect() as conn:
        customers, products = _load_refs(conn)
    if not customers or not products:
        print("[drip] no customers/products found — run generate_history.py first. Exiting.")
        return
    print(f"[drip] starting, interval={INTERVAL}s")
    while True:
        try:
            insert_batch(engine, s3, customers, products)
        except Exception as exc:  # noqa: BLE001
            print(f"[drip][error] {exc}")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
