"""
run.py — NOUREDDINE data simulator: single entry point with stateful catch-up.

ONE process, ONE source of truth (replaces the old history + drip modes).

It always brings the warehouse up to wall-clock NOW():
  - First run (empty state)  -> BOOTSTRAP: upsert the fixed Islamic-calendar
    windows, create reference customers/products/inventory, and backfill ~3 years
    of orders (NOW-3y .. NOW) using the seasonality + growth + hourly demand model.
  - Every run after that     -> CATCH-UP: generate only the missing slice
    (last_generated_at, NOW], same demand model, then advance the watermark.

Run modes:
  python -m simulator.run            # loop forever, catching up every CATCH_UP_INTERVAL_SECONDS
  python -m simulator.run --once     # run a single bootstrap-or-catch-up cycle, then exit
  python -m simulator.run --reset    # truncate business tables + reset state, then bootstrap

Idempotency: order/line IDs are derived deterministically from the hour bucket, so
re-processing an overlapping window inserts nothing new (ON CONFLICT DO NOTHING).
The state watermark is advanced only AFTER the DB writes commit (same transaction).

Calendar dates are NEVER computed — they come from simulator/seasonality.py (CLAUDE.md).
"""
from __future__ import annotations

import argparse
import os
import random
import time
import uuid
from datetime import date, datetime, timedelta, timezone

import numpy as np
from sqlalchemy import text

from .common import (
    BUSINESS_TABLES, CATEGORIES, CATEGORY_PRICE_BAND, CHANNELS,
    ensure_bucket, get_engine, get_s3, put_bronze,
)
from .seasonality import CALENDAR_EVENTS, demand_multiplier, get_calendar_event_name
from .state import ensure_state, read_state, reset_state, set_last_generated

try:
    from faker import Faker
    fake = Faker(["fr_FR", "en_GB"])
except Exception:  # pragma: no cover - faker always present in the image
    fake = None

# Deterministic namespace so the same hour bucket always maps to the same IDs.
NS = uuid.UUID("00000000-0000-0000-0000-00000000515d")

CATCH_UP_INTERVAL_SECONDS = int(os.environ.get("CATCH_UP_INTERVAL_SECONDS", 600))
BACKFILL_YEARS = int(os.environ.get("SIM_BACKFILL_YEARS", 3))
BASE_DAILY_ORDERS = float(os.environ.get("SIM_BASE_DAILY_ORDERS", 15))
N_CUSTOMERS = int(os.environ.get("SIM_N_CUSTOMERS", 8000))
N_PRODUCTS = int(os.environ.get("SIM_N_PRODUCTS", 300))
SEASON_TAGS = ["ramadan", "eid", "nikah", "year-round", "year-round"]

# Per-hour-of-day weighting: overnight dip, evening e-commerce peak 18:00–22:00.
HOUR_WEIGHTS = np.array([
    0.2, 0.1, 0.1, 0.1, 0.1, 0.2,   # 00–05 overnight
    0.4, 0.7, 1.0, 1.1, 1.1, 1.2,   # 06–11 morning
    1.3, 1.1, 1.0, 1.0, 1.1, 1.4,   # 12–17 afternoon
    2.2, 2.6, 2.6, 2.2, 1.2, 0.6,   # 18–23 evening peak
])
HOUR_WEIGHTS = HOUR_WEIGHTS / HOUR_WEIGHTS.sum()

CARRIERS = ["Colissimo", "Chronopost", "DHL", "DPD", "Mondial Relay"]
PAY_STATUS = ["paid", "paid", "paid", "pending", "refunded"]
ORD_STATUS = ["delivered", "shipped", "processing", "cancelled"]


# ---------------------------------------------------------------------------
# Reference data (calendar / customers / products / inventory)
# ---------------------------------------------------------------------------
def ensure_categories(conn) -> dict:
    for name, _tag in CATEGORIES:
        conn.execute(text(
            "INSERT INTO oltp.categories (category_name) VALUES (:n) "
            "ON CONFLICT (category_name) DO NOTHING"
        ), {"n": name})
    rows = conn.execute(text("SELECT category_id, category_name FROM oltp.categories")).fetchall()
    return {r.category_name: r.category_id for r in rows}


def ensure_calendar_events(conn) -> None:
    """Upsert the FIXED Islamic-calendar windows (+ Nikah / Black Friday). Never computed."""
    all_events = list(CALENDAR_EVENTS)
    for year in range(date.today().year - BACKFILL_YEARS - 1, date.today().year + 2):
        all_events.append({"name": f"Nikah Season {year}", "type": "nikah",
                           "start": date(year, 6, 1), "end": date(year, 8, 31)})
        bf = date(year, 11, 30)
        while bf.weekday() != 4:
            bf -= timedelta(days=1)
        all_events.append({"name": f"Black Friday {year}", "type": "black_friday",
                           "start": bf, "end": bf})
    for ev in all_events:
        conn.execute(text(
            "INSERT INTO oltp.calendar_events (event_name, event_type, start_date, end_date) "
            "SELECT :name, :type, :start, :end "
            "WHERE NOT EXISTS (SELECT 1 FROM oltp.calendar_events WHERE event_name = :name)"
        ), {"name": ev["name"], "type": ev["type"], "start": ev["start"], "end": ev["end"]})


def ensure_reference_actors(conn, cat_ids: dict):
    """Create customers/products/inventory once; reuse them on later runs."""
    n_cust = conn.execute(text("SELECT COUNT(*) FROM oltp.customers")).scalar()
    if n_cust == 0:
        print(f"[bootstrap] generating {N_CUSTOMERS} customers, {N_PRODUCTS} products")
        customers = []
        for _ in range(N_CUSTOMERS):
            created = (fake.date_time_between(start_date="-3y", end_date="now")
                       if fake else datetime.now())
            customers.append({
                "customer_id": uuid.uuid4(),
                "email": f"{uuid.uuid4().hex[:10]}@example.test",
                "first_name": fake.first_name_male() if fake else "Test",
                "last_name": fake.last_name() if fake else "User",
                "country": random.choice(["France", "France", "France", "United Kingdom", "Germany", "Belgium"]),
                "city": fake.city() if fake else "Paris",
                "consent_marketing": random.random() < 0.6,
                "acquisition_source": random.choice(CHANNELS),
                "created_at": created, "updated_at": created,
            })
        conn.execute(text(
            "INSERT INTO oltp.customers (customer_id,email,first_name,last_name,country,city,"
            "consent_marketing,acquisition_source,created_at,updated_at) VALUES "
            "(:customer_id,:email,:first_name,:last_name,:country,:city,:consent_marketing,"
            ":acquisition_source,:created_at,:updated_at)"), customers)

        products = []
        for i in range(N_PRODUCTS):
            cat_name, _ = random.choice(CATEGORIES)
            lo, hi = CATEGORY_PRICE_BAND[cat_name]
            price = round(random.uniform(lo, hi), 2)
            products.append({
                "product_id": uuid.uuid4(), "sku": f"NRD-{cat_name[:3].upper()}-{i:05d}",
                "product_name": f"{cat_name} {fake.color_name() if fake else 'Classic'} {i}",
                "category_id": cat_ids[cat_name], "price_eur": price,
                "cost_eur": round(price * random.uniform(0.45, 0.65), 2),
                "seasonality_tag": random.choice(SEASON_TAGS),
                "created_at": datetime.now(), "updated_at": datetime.now(),
            })
        conn.execute(text(
            "INSERT INTO oltp.products (product_id,sku,product_name,category_id,price_eur,"
            "cost_eur,seasonality_tag,created_at,updated_at) VALUES "
            "(:product_id,:sku,:product_name,:category_id,:price_eur,:cost_eur,:seasonality_tag,"
            ":created_at,:updated_at)"), products)
        conn.execute(text(
            "INSERT INTO oltp.inventory (product_id,stock_quantity,reorder_threshold) "
            "VALUES (:pid,:stock,:thr)"),
            [{"pid": p["product_id"], "stock": random.randint(0, 500),
              "thr": random.randint(10, 50)} for p in products])

    customers = [r[0] for r in conn.execute(text("SELECT customer_id FROM oltp.customers")).fetchall()]
    products = conn.execute(text(
        "SELECT p.product_id, p.price_eur, c.category_name FROM oltp.products p "
        "JOIN oltp.categories c ON p.category_id = c.category_id")).fetchall()
    return customers, products


# ---------------------------------------------------------------------------
# Slice generation (hour-by-hour, deterministic, idempotent)
# ---------------------------------------------------------------------------
def _avg_multiplier(d: date) -> float:
    return float(np.mean([demand_multiplier(d, cat) for cat, _ in CATEGORIES]))


def _pick_product(products, d: date):
    weights = np.array([demand_multiplier(d, p.category_name) for p in products])
    weights /= weights.sum()
    return products[int(np.random.choice(len(products), p=weights))]


def generate_slice(engine, s3, start_dt: datetime, end_dt: datetime, customers, products) -> int:
    """Generate orders for whole hour buckets in (start_dt, end_dt]. Returns order count."""
    start_hour = start_dt.replace(minute=0, second=0, microsecond=0, tzinfo=None) + timedelta(hours=1)
    end_hour = end_dt.replace(minute=0, second=0, microsecond=0, tzinfo=None)
    if end_hour < start_hour:
        return 0

    total_orders = 0
    by_day_bronze: dict[str, list] = {}
    hour = start_hour
    with engine.begin() as conn:
        while hour <= end_hour:
            d = hour.date()
            expected = BASE_DAILY_ORDERS * _avg_multiplier(d) * HOUR_WEIGHTS[hour.hour]
            n = np.random.poisson(max(0.0, expected))
            for i in range(int(n)):
                oid = uuid.uuid5(NS, f"{hour:%Y%m%d%H}:{i}")
                cust = random.choice(customers)
                ts = hour + timedelta(minutes=(i * 7) % 60, seconds=(i * 13) % 60)
                n_lines = random.randint(1, 4)
                total = 0.0
                lines = []
                for j in range(n_lines):
                    prod = _pick_product(products, d)
                    qty = random.randint(1, 3)
                    unit = float(prod.price_eur)
                    lt = round(unit * qty, 2)
                    total += lt
                    lines.append((uuid.uuid5(NS, f"{oid}:item:{j}"), oid, prod.product_id, qty, unit, lt))
                discount = round(total * random.choice([0, 0, 0, 0.1, 0.15]), 2)
                shipping = round(random.choice([0, 4.95, 6.95, 9.95]), 2)
                channel = random.choice(CHANNELS)
                conn.execute(text(
                    "INSERT INTO oltp.orders (order_id,customer_id,order_date,total_amount,"
                    "discount_amount,shipping_cost,payment_status,order_status,acquisition_channel,"
                    "created_at) VALUES (:oid,:cid,:od,:tot,:disc,:ship,:ps,:os,:ch,:od) "
                    "ON CONFLICT (order_id) DO NOTHING"),
                    {"oid": oid, "cid": cust, "od": ts, "tot": round(total, 2), "disc": discount,
                     "ship": shipping, "ps": random.choice(PAY_STATUS),
                     "os": random.choice(ORD_STATUS), "ch": channel})
                conn.execute(text(
                    "INSERT INTO oltp.order_items (order_item_id,order_id,product_id,quantity,"
                    "unit_price,line_total) VALUES (:oiid,:oid,:pid,:q,:u,:lt) "
                    "ON CONFLICT (order_item_id) DO NOTHING"),
                    [{"oiid": li[0], "oid": li[1], "pid": li[2], "q": li[3], "u": li[4], "lt": li[5]}
                     for li in lines])
                conn.execute(text(
                    "INSERT INTO oltp.shipments (shipment_id,order_id,carrier,tracking_number,"
                    "shipping_date,delivery_date,shipment_status) VALUES "
                    "(:sid,:oid,:car,:trk,:sd,:dd,:st) ON CONFLICT (shipment_id) DO NOTHING"),
                    {"sid": uuid.uuid5(NS, f"{oid}:ship"), "oid": oid,
                     "car": random.choice(CARRIERS),
                     "trk": uuid.uuid5(NS, f"{oid}:trk").hex[:14].upper(),
                     "sd": d + timedelta(days=random.randint(0, 2)),
                     "dd": d + timedelta(days=random.randint(2, 6)),
                     "st": random.choice(["delivered", "in_transit", "pending"])})
                total_orders += 1
                by_day_bronze.setdefault(d.isoformat(), []).append(str(oid))
            hour += timedelta(hours=1)
        # advance the watermark in the SAME transaction as the writes
        set_last_generated(conn, end_dt)

    # bronze dump (best-effort) — partitioned year=YYYY/month=MM/day=DD
    for day_iso, ids in by_day_bronze.items():
        dd = date.fromisoformat(day_iso)
        key = f"orders/year={dd.year:04d}/month={dd.month:02d}/day={dd.day:02d}/batch.json"
        put_bronze(s3, key, {"date": day_iso, "event": get_calendar_event_name(dd),
                             "order_ids": ids, "count": len(ids)})
    return total_orders


# ---------------------------------------------------------------------------
# Bootstrap / catch-up / loop
# ---------------------------------------------------------------------------
def _now() -> datetime:
    return datetime.now()


def run_cycle(engine, s3) -> None:
    with engine.begin() as conn:
        ensure_state(conn)
        cat_ids = ensure_categories(conn)
        ensure_calendar_events(conn)
        customers, products = ensure_reference_actors(conn, cat_ids)
        state = read_state(conn)

    now = _now()
    if state["last_generated_at"] is None or not state["bootstrap_completed"]:
        start = now - timedelta(days=365 * BACKFILL_YEARS)
        print(f"[bootstrap] backfilling {BACKFILL_YEARS}y: {start:%Y-%m-%d} -> {now:%Y-%m-%d %H:%M}")
        n = generate_slice(engine, s3, start, now, customers, products)
        with engine.begin() as conn:
            set_last_generated(conn, now, bootstrap_completed=True)
        print(f"[bootstrap] done: {n} orders generated, watermark={now:%Y-%m-%d %H:%M}")
    else:
        last = state["last_generated_at"].replace(tzinfo=None)
        delta = (now - last).total_seconds()
        if delta <= 0:
            print(f"[catch-up] no-op (watermark {last} >= now {now}); clock drift?")
            return
        print(f"[catch-up] {last:%Y-%m-%d %H:%M} -> {now:%Y-%m-%d %H:%M} ({delta/3600:.2f}h)")
        n = generate_slice(engine, s3, last, now, customers, products)
        print(f"[catch-up] done: {n} orders, watermark={now:%Y-%m-%d %H:%M}")


def reset(engine) -> None:
    print("[reset] truncating business tables + resetting simulator.state")
    with engine.begin() as conn:
        ensure_state(conn)
        conn.execute(text("TRUNCATE TABLE oltp." + ", oltp.".join(BUSINESS_TABLES)
                          + " RESTART IDENTITY CASCADE"))
        reset_state(conn)


def main() -> None:
    ap = argparse.ArgumentParser(description="NOUREDDINE stateful catch-up simulator")
    ap.add_argument("--reset", action="store_true",
                    help="truncate business tables + reset state, then re-bootstrap")
    ap.add_argument("--once", action="store_true",
                    help="run a single bootstrap-or-catch-up cycle and exit (no loop)")
    args = ap.parse_args()

    engine = get_engine()
    s3 = get_s3()
    ensure_bucket(s3)

    if args.reset:
        reset(engine)

    if args.once:
        run_cycle(engine, s3)
        return

    print(f"[run] starting catch-up loop, interval={CATCH_UP_INTERVAL_SECONDS}s")
    while True:
        try:
            run_cycle(engine, s3)
        except Exception as exc:  # noqa: BLE001 - keep the loop alive
            print(f"[run][error] {exc}")
        time.sleep(CATCH_UP_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
